interface SectionPageProps {
  eyebrow: string
  title: string
  description: string
}


export function SectionPage({
  eyebrow,
  title,
  description,
}: SectionPageProps) {
  return (
    <section className="section-page">
      <header className="page-heading">
        <p className="eyebrow">
          {eyebrow}
        </p>

        <h1>
          {title}
        </h1>

        <p className="page-description">
          {description}
        </p>
      </header>

      <div className="section-placeholder">
        <h2>
          {title} workspace
        </h2>

        <p>
          The application shell is ready.
          Live AquaMind data and controls
          will be connected in the
          corresponding frontend phase.
        </p>
      </div>
    </section>
  )
}