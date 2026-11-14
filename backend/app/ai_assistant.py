"""LaunchDarkly's current AI SDK composition, with explicit scripted fallback.

https://launchdarkly.com/docs/sdk/ai/python
The SDK resolves the config on EVERY request; never cache a managed prompt or model here.
"""

import asyncio
import time
from dataclasses import asdict

from ldclient import Context
from launchdarkly_ai_server import SDKOptions, config, configure, create_handler, init_client, shutdown
from openai import APIConnectionError, APITimeoutError, AuthenticationError, BadRequestError, NotFoundError, RateLimitError

from .adapters import PreviewAssistant
from .openai_provider import GenerationResponseError, OpenAIProvider


# DEMO START ai-shared-client: Share feature evaluation with the separate AI SDK without transferring client ownership.
class SharedFeatureClient:
    """Borrow the feature client without giving the AI singleton ownership of its close()."""

    def __init__(self, client):
        self.client = client

    def variation(self, key, context, default):
        return self.client.variation(key, Context.from_dict(context), default)

    def track(self, key, context, data=None, metric_value=None):
        self.client.track(key, Context.from_dict(context), data, metric_value)

    def flush(self):
        return self.client.flush()

    def close(self):
        # AI SDK 1.1.0 calls close even for a supplied client. Feature lifespan owns the real close.
        pass

    def get_environment_id(self):
        return getattr(self.client, 'get_environment_id', lambda: None)()
# DEMO END ai-shared-client


# DEMO START ai-config: Evaluate managed prompts per request and record success, usage, errors, and labeled fallbacks.
class LaunchDarklyAssistant:
    """Own AI/provider lifecycle; expose only safe status and per-answer metadata."""

    def __init__(self, settings, features, provider=None):
        self.settings = settings
        self.features = features
        self.provider = provider
        self.caller = None
        self.state = 'needs_openai_key' if not settings.openai_key and provider is None else 'not_started'
        self.preview = PreviewAssistant()

    # DEMO START ai-sdk-startup: Initialize the separate AI SDK with shared feature evaluation and content capture disabled.
    async def start(self):
        if self.state == 'needs_openai_key':
            return
        try:
            configure(options=SDKOptions(capture_content=False))
            await init_client(client=SharedFeatureClient(self.features.client))
            self.provider = self.provider or OpenAIProvider(self.settings.openai_key)
            handler = create_handler(('OpenAI', 'messages'), self.generate, capture_content=False)
            # No tools or provider routing beyond OpenAI text completion in this scoped integration.
            self.caller = config(key=self.settings.ai_config_key, handler=handler)
            self.state = 'sdk_ready'
        except Exception:
            # Never surface provider exceptions, which can include credentials or chat content.
            self.state = 'unavailable'
    # DEMO END ai-sdk-startup

    def status(self):
        # Ready means wired locally, not that the config exists or metrics reached the platform.
        return {'status': self.state, 'config_key': self.settings.ai_config_key}

    # DEMO START rejected-usage: Preserve tokens and original invocation attribution when a provider response is rejected.
    async def generate(self, config, user_input, tool_handlers=None, variables=None, history=None):
        """Preserve incurred tokens on rejected outputs; the AI SDK owns error/duration events."""
        try:
            return await self.provider.generate(config, user_input, tool_handlers, variables, history)
        except GenerationResponseError as error:
            # Pinned AI SDK 1.1.0 passes this invocation's attribution in reserved handler variables.
            # Its exception path emits error/duration but omits usage. Do not re-evaluate the config:
            # targeting may have changed while the provider was answering.
            attribution = (variables or {}).get('__ld')
            context = (variables or {}).get('ldContext')
            if attribution and context:
                for kind in ('input', 'output', 'total'):
                    value = error.usage.get(kind, 0)
                    if value > 0:
                        try:
                            self.features.client.track(
                                f'$ld:ai:tokens:{kind}', Context.from_dict(context), attribution, value,
                            )
                        except Exception:
                            # A telemetry failure must not replace the safe generation failure.
                            pass
            raise
    # DEMO END rejected-usage

    # DEMO START managed-invocation: Evaluate the managed config on each independent question and return safe variation metadata.
    async def respond(self, message, profile):
        if self.caller is None:
            return await self.fallback(message, profile, self.state)
        began = time.perf_counter()
        try:
            context = self.features.context(profile).to_dict()
            # This async limit also bounds config lookup and any handler work around the provider call.
            async with asyncio.timeout(25):
                result = await self.caller.invoke(message, context, {'visitor_tier': profile.tier})
            data = result.track_data or {}
            return {
                'reply': result.response, 'source': 'LaunchDarkly AI Config · OpenAI', 'fallback': False,
                'config_key': self.settings.ai_config_key, 'model': data.get('modelName'),
                'variation': data.get('variationKey'), 'version': data.get('version'),
                'usage': asdict(result.usage), 'duration_ms': round((time.perf_counter() - began) * 1000),
            }
        except GenerationResponseError as error:
            result = await self.fallback(message, profile, error.reason)
            # These tokens belong to the rejected attempt, not to the scripted fallback text.
            return {**result, 'attempt_usage': error.usage}
        except (TimeoutError, APITimeoutError):
            return await self.fallback(message, profile, 'generation_timeout')
        except AuthenticationError:
            return await self.fallback(message, profile, 'provider_authentication')
        except RateLimitError:
            return await self.fallback(message, profile, 'provider_quota_or_rate_limit')
        except NotFoundError:
            return await self.fallback(message, profile, 'model_unavailable')
        except BadRequestError:
            return await self.fallback(message, profile, 'provider_request_rejected')
        except APIConnectionError:
            return await self.fallback(message, profile, 'provider_unreachable')
        except Exception:
            return await self.fallback(message, profile, 'generation_unavailable')
    # DEMO END managed-invocation

    # DEMO START ai-fallback: Label scripted recovery separately from a successful paid model generation.
    async def fallback(self, message, profile, reason):
        result = await self.preview.respond(message, profile)
        explanation = {
            'generation_incomplete': 'The model answer was incomplete. Showing scripted offer information instead.',
            'generation_failed': 'The model could not finish its answer. Showing scripted offer information instead.',
            'generation_empty': 'The model returned no answer. Showing scripted offer information instead.',
        }.get(reason)
        return {**result, 'source': 'Scripted fallback · AI unavailable', 'fallback_reason': reason,
                'fallback_message': explanation}
    # DEMO END ai-fallback

    # DEMO START ai-sdk-cleanup: Close AI-owned resources without closing the borrowed feature client twice.
    async def close(self):
        try:
            # SharedFeatureClient prevents the AI singleton from closing the feature SDK twice.
            if self.state not in {'needs_openai_key', 'not_started'}:
                await shutdown()
        finally:
            if self.provider is not None:
                await self.provider.close()
            self.caller = None
    # DEMO END ai-sdk-cleanup
# DEMO END ai-config
