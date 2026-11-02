import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="foundation-page">
      <div className="foundation-card">
        <p className="eyebrow">
          404
        </p>

        <h1>
          Page not found
        </h1>

        <p className="foundation-description">
          The requested AquaMind page does not exist.
        </p>

        <Link to="/">
          Return home
        </Link>
      </div>
    </section>
  )
}