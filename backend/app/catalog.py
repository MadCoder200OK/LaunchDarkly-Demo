"""Fictional demo fixtures; these are neither customer records nor real bank offers."""

from .domain import Offer, Profile

# Re-create individual targeting for qa-001 and the tier=Premium rule in your LD environment.
# Experiment visitors stay on the default until an experiment audience is configured there.
# DEMO START demo-contexts: Define stable fictional QA, Premium, Standard, and twenty experiment identities.
PROFILES = [
    Profile(key="qa-001", name="Alex Morgan", role="Internal QA", tier="Standard", beta_tester=True),
    Profile(key="premium-001", name="Priya Sharma", role="Premium customer", tier="Premium"),
    Profile(key="standard-001", name="Sam Taylor", role="Standard customer", tier="Standard"),
    Profile(key="experiment-001", name="Jordan Lee", role="Experiment visitor", tier="Standard", experiment_eligible=True),
    # Stable, bounded fictional identities let the presenter revisit assignments in one iteration.
    # LD chooses each variation: do not assign treatments here or rotate keys on every click.
    *[
        Profile(key=f"experiment-{number:03d}", name=f"Demo visitor {number:02d}", role="Experiment visitor", tier="Standard", experiment_eligible=True)
        for number in range(2, 21)
    ],
]
# DEMO END demo-contexts

OFFERS = [
    Offer(id="travel", category="TRAVEL & LIFESTYLE", title="Your next adventure,\na little closer.", description="Make room for more memorable journeys with the ABC Voyager Card.", highlight="3×", detail="reward points on travel", accent="peach"),
    Offer(id="save", category="SAVINGS", title="Big plans start\nwith small steps.", description="Give your next milestone a dedicated place to grow with Goal Saver.", highlight="Zero", detail="monthly account fees", accent="mint"),
    Offer(id="everyday", category="EVERYDAY BANKING", title="More from your\neveryday moments.", description="From your morning coffee to weekend plans, make every purchase count.", highlight="2×", detail="points on everyday spends", accent="lilac"),
]
