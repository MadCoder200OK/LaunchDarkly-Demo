"""Exercise the actual AI SDK with local client/provider doubles, never paid API calls."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from fastapi.testclient import TestClient
from ldclient import Context

from app.ai_assistant import LaunchDarklyAssistant
from app.catalog import PROFILES
from app.main import create_app
from app.openai_provider import OpenAIProvider
from app.settings import Settings


def test_live_config_changes_metrics_disabled_fallback_and_single_client_ownership():
    """Prompt/model edits must apply next request; telemetry must omit the conversation."""
    class FakeLD:
        value = {'model': {'name': 'demo-model-a', 'parameters': {'max_tokens': 256}},
                 'provider': {'name': 'OpenAI'}, 'messages': [{'role': 'system', 'content': 'Brief for {{visitor_tier}}'}],
                 '_ldMeta': {'enabled': True, 'variationKey': 'concise', 'version': 1, 'mode': 'completion'}}
        closed = False

        def __init__(self):
            self.events = []

        def variation(self, key, context, default):
            assert key == 'offer-assistant' and context.key == 'qa-001'
            return deepcopy(self.value)

        def track(self, *args):
            self.events.append(args)

        def flush(self):
            pass

        def close(self):
            self.closed = True

        def get_environment_id(self):
            return 'test-environment'

    class FakeOpenAI:
        def __init__(self):
            self.calls = []
            self.responses = SimpleNamespace(create=self.generate)
            self.closed = False
            self.fail = False

        async def generate(self, **kwargs):
            self.calls.append(kwargs)
            if self.fail:
                raise RuntimeError('provider-secret private question marker')
            return SimpleNamespace(status='completed', output_text='fictional answer', usage=SimpleNamespace(input_tokens=11, output_tokens=4, total_tokens=15))

        async def close(self):
            self.closed = True

    async def scenario():
        ld = FakeLD()
        provider = FakeOpenAI()
        features = SimpleNamespace(client=ld, context=lambda profile: Context.builder(profile.key).name(profile.name).build())
        assistant = LaunchDarklyAssistant(Settings(ai_enabled=True), features, OpenAIProvider('', client=provider))
        await assistant.start()
        try:
            first = await assistant.respond('private question marker', PROFILES[0])
            assert not first['fallback'] and first['usage']['total'] == 15
            assert first['model'] == 'demo-model-a' and first['version'] == 1
            assert provider.calls[0]['input'][0]['content'] == 'Brief for Standard'
            assert provider.calls[0]['store'] is False
            ld.value['model']['name'] = 'demo-model-b'
            ld.value['messages'][0]['content'] = 'Explain with examples'
            ld.value['_ldMeta']['version'] = 2
            second = await assistant.respond('private question marker', PROFILES[0])
            assert second['model'] == 'demo-model-b' and second['version'] == 2
            assert provider.calls[1]['input'][0]['content'] == 'Explain with examples'
            events = [event for event in ld.events if event[0] in {
                '$ld:ai:generation:success', '$ld:ai:duration:total', '$ld:ai:tokens:total',
                '$ld:ai:tokens:input', '$ld:ai:tokens:output',
            }]
            assert sum(event[0] == '$ld:ai:generation:success' for event in events) == 2
            assert sum(event[0] == '$ld:ai:tokens:total' and event[3] == 15 for event in events) == 2
            assert all(event[1].key == 'qa-001' for event in events)
            assert 'private question marker' not in repr(ld.events) and 'fictional answer' not in repr(ld.events)
            ld.value['_ldMeta']['enabled'] = False
            fallback = await assistant.respond('travel', PROFILES[0])
            assert fallback['fallback'] and 'Scripted fallback' in fallback['source']
            assert len(provider.calls) == 2
            ld.value['_ldMeta']['enabled'] = True
            provider.fail = True
            failure = await assistant.respond('travel', PROFILES[0])
            assert failure['fallback'] and len(provider.calls) == 3
            assert 'provider-secret' not in repr(failure)
            assert any(event[0] == '$ld:ai:generation:error' for event in ld.events)
        finally:
            await assistant.close()
        assert not ld.closed  # The feature SDK owner must still be able to flush and close it once.
        assert provider.closed

    asyncio.run(scenario())


def test_missing_key_never_calls_provider_and_public_status_does_not_expose_secrets():
    """An incomplete setup preserves the offers app and labels scripted answers honestly."""
    assistant = LaunchDarklyAssistant(Settings(ai_enabled=True), SimpleNamespace())
    with TestClient(create_app(settings=Settings(openai_key='provider-secret'), assistant=assistant)) as client:
        assert client.get('/api/config').json()['ai']['status'] == 'needs_openai_key'
        assert 'provider-secret' not in client.get('/api/config').text
        reply = client.post('/api/chat', json={'profile_key': 'qa-001', 'message': 'travel'}).json()
        assert reply['fallback'] and 'Scripted fallback' in reply['source']
        assert 'provider-secret' not in repr(Settings(openai_key='provider-secret'))


@pytest.mark.parametrize('status,text,reason', [
    ('incomplete', 'private partial answer', 'generation_incomplete'),
    ('incomplete', '', 'generation_incomplete'),
    ('failed', 'private partial answer', 'generation_failed'),
    ('completed', '', 'generation_empty'),
])
def test_rejected_provider_outputs_preserve_usage_without_success_or_retries(status, text, reason):
    """Exercise the real AI SDK error path with measured usage and the original attribution."""
    class FakeLD:
        def __init__(self):
            self.events = []
            self.evaluations = 0

        def variation(self, key, context, default):
            self.evaluations += 1
            return {'model': {'name': 'stub-model'}, 'provider': {'name': 'OpenAI'},
                    'messages': [{'role': 'system', 'content': 'A fictional offer assistant'}],
                    '_ldMeta': {'enabled': True, 'variationKey': 'concise', 'version': 7, 'mode': 'completion'}}

        def track(self, *args):
            self.events.append(args)

        def flush(self):
            pass

    class FakeOpenAI:
        def __init__(self):
            self.responses = SimpleNamespace(create=self.generate)
            self.calls = 0

        async def generate(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(status=status, output_text=text,
                                   usage=SimpleNamespace(input_tokens=20, output_tokens=5, total_tokens=25))

        async def close(self):
            pass

    async def scenario():
        ld, provider = FakeLD(), FakeOpenAI()
        features = SimpleNamespace(client=ld, context=lambda profile: Context.builder(profile.key).build())
        assistant = LaunchDarklyAssistant(Settings(ai_enabled=True), features, OpenAIProvider('', client=provider))
        await assistant.start()
        try:
            result = await assistant.respond('private question marker', PROFILES[0])
            assert result['fallback'] and result['fallback_reason'] == reason
            assert result['attempt_usage'] == {'input': 20, 'output': 5, 'total': 25}
            assert provider.calls == 1 and ld.evaluations == 1
            generations = [event for event in ld.events if event[0].startswith('$ld:ai:generation:')]
            assert [event[0] for event in generations] == ['$ld:ai:generation:error']
            tokens = [event for event in ld.events if event[0].startswith('$ld:ai:tokens:')]
            assert sorted((event[0].rsplit(':', 1)[1], event[3]) for event in tokens) == [('input', 20), ('output', 5), ('total', 25)]
            assert all(event[1].key == 'qa-001' and event[2]['variationKey'] == 'concise' and event[2]['version'] == 7 for event in tokens)
            assert len({event[2]['runId'] for event in tokens + generations}) == 1
            assert 'private partial answer' not in repr(result) + repr(ld.events)
            assert 'private question marker' not in repr(ld.events)
        finally:
            await assistant.close()

    asyncio.run(scenario())
