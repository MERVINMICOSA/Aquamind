import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { WaterFlowPage } from './WaterFlowPage'

describe('External continuous water flow guide', () => {
  it('describes gravity return and independent circulation without controls', () => {
    render(
      <MemoryRouter>
        <WaterFlowPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Water flow' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Continuous water circulation' })).toBeInTheDocument()
    expect(screen.getByText(/External circulation pump/)).toBeInTheDocument()
    expect(screen.getByText(/Gravity return/)).toBeInTheDocument()
    expect(screen.getByText(/not the same as verifying water flow/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Review sensor readings' }))
      .toHaveAttribute('href', '/sensors')
    expect(screen.queryByRole('button', { name: /start|stop|turn on|turn off/i }))
      .not.toBeInTheDocument()
  })
})
