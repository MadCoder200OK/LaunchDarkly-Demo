// Both homepage treatments render the experience already evaluated by Python.
import { ArrowRight, Plane, ShieldCheck } from "lucide-react";

// DEMO START offers-hero: Show the selected offers experience above the fold.
export default function OffersHero({ experience }) {
  const featured = experience?.decision.variant === "new" && experience.offers[0];
  if (featured) {
    return (
      <section className="featured-hero" aria-labelledby="hero-heading">
        <div className="featured-hero-inner">
          <div className="featured-hero-copy">
            <p className="eyebrow">YOUR PERSONALIZED OFFERS</p>
            <h1 id="hero-heading">
              Offers picked for you, <em>{experience.profile.name.split(" ")[0]}.</em>
            </h1>
            <p>Explore choices for your next trip, your savings goals, and everyday spending.</p>
            <a className="primary" href="#offers">
              See my offers <ArrowRight size={17} aria-hidden="true" />
            </a>
          </div>
          <div className="featured-hero-offer">
            <div className="featured-hero-offer-top">
              <span>{featured.category}</span>
              <Plane size={22} aria-hidden="true" />
            </div>
            <p className="featured-hero-benefit">
              <strong>{featured.highlight}</strong>
              <span>{featured.detail}</span>
            </p>
            <p className="featured-hero-title">{featured.title.replace("\n", " ")}</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="hero">
      <div className="hero-copy">
        <p className="eyebrow">
          <span className="tiny-line" /> BANKING, WITH YOU IN MIND
        </p>
        <h1>
          A little more
          <br />
          for <em>your everyday.</em>
        </h1>
        <p>
          For the plans you're making.
          <br />
          And the life happening in between.
        </p>
        <a className="primary" href="#offers">
          Find your next possibility <ArrowRight size={17} />
        </a>
        <div className="hero-note">
          <ShieldCheck size={16} /> Thoughtful banking. Built around you.
        </div>
      </div>
      <div
        className="hero-art"
        aria-label="Illustration of an ABC Bank card among sculptural shapes"
        role="img"
      >
        <div className="art-ring" />
        <div className="art-disc" />
        <div className="art-pedestal" />
        <div className="bank-card">
          <div className="card-top">
            <span>abc bank.</span>
            <span>VISA</span>
          </div>
          <div className="chip" />
          <div className="card-lines">
            •••• &nbsp; •••• &nbsp; •••• &nbsp; 2048
          </div>
          <div className="card-bottom">
            <span>A WORLD OF POSSIBILITIES</span>
            <span>↗</span>
          </div>
        </div>
        <div className="art-caption">
          <span className="star">✳</span>
          <div>
            Made for where
            <br />
            life takes you.
          </div>
        </div>
      </div>
    </section>
  );
}
// DEMO END offers-hero
