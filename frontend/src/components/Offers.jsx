// Render the offers from Python's decision while preserving the same offer actions in each layout.
import { ArrowUpRight, Plane, Sprout, Coffee } from "lucide-react";

const icons = { travel: Plane, save: Sprout, everyday: Coffee };

// DEMO START offers-panel: Render the existing or personalized offer panel from the server decision.
export default function Offers({ experience, onExplore }) {
  const personalized = experience.decision.variant === "new";

  return (
    <section id="offers" className="offers-section" aria-labelledby="offers-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{personalized ? "YOUR SELECTION" : "ABC BANK OFFERS"}</p>
          <h2 id="offers-heading">
            {personalized ? "Good things, picked for you." : "Browse all offers"}
          </h2>
        </div>
      </div>
      <p className="section-description">
        {personalized ? "Start with travel rewards or explore more ways to save." : "Compare travel, savings, and everyday banking offers."}
      </p>
      {experience.incident && (
        <div className="incident-banner" role="status">
          A simulated issue is active. Explore an offer to see the error.
        </div>
      )}
      <div className={personalized ? "offers-grid" : "offers-list"}>
        {experience.offers.map((offer, index) => {
          const Icon = icons[offer.id];
          const featured = personalized && index === 0;
          return (
            <article className={personalized ? `offer-card ${offer.accent}${featured ? " offer-card--featured" : ""}` : "offer-row"} key={offer.id}>
              <div className="offer-top">
                {Icon && <Icon size={23} strokeWidth={1.5} aria-hidden="true" />}
                <span>{featured ? "FEATURED OFFER" : offer.category}</span>
              </div>
              <div className="offer-copy">
                <h3>{offer.title}</h3>
                <p>{offer.description}</p>
              </div>
              <div className="offer-benefit">
                <strong>{offer.highlight}</strong><span>{offer.detail}</span>
              </div>
              <button className="offer-link" onClick={() => onExplore(offer)}>
                Explore offer <ArrowUpRight size={19} aria-hidden="true" />
              </button>
            </article>
          );
        })}
      </div>
      <p className="fine-print">Illustrative offers for this demo only. No real products, rates, or applications.</p>
    </section>
  );
}
// DEMO END offers-panel
