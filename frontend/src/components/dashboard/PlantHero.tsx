import { LettuceModel } from './LettuceModel'


export function PlantHero() {
  return (
    <article className="plant-hero">
      <div className="plant-hero__content">
        <p className="plant-hero__eyebrow">
          AquaMind Ecosystem
        </p>

        <h2>
          Your system at a glance
        </h2>

        <p className="plant-hero__description">
          Live AquaMind monitoring and control
          data for the selected aquaponics system.
        </p>

        <div className="plant-hero__visual">
          <div
            className="plant-visual"
            aria-hidden="true"
          >
            <div className="plant-visual__glow" />

            <div className="plant-visual__orbit plant-visual__orbit--outer" />

            <div className="plant-visual__orbit plant-visual__orbit--inner" />

            <LettuceModel />

            <div className="plant-visual__platform">
              <span />
            </div>
          </div>
        </div>

        <div className="plant-hero__caption">
          <span
            className="plant-hero__pulse"
            aria-hidden="true"
          />

          <span>
            AquaMind system visualization
          </span>
        </div>
      </div>
    </article>
  )
}