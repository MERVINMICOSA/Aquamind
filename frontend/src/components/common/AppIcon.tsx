interface AppIconProps {
  name:
    | 'dashboard'
    | 'sensors'
    | 'actuators'
    | 'feeding'
    | 'refill'
    | 'automation'
    | 'alerts'
    | 'settings'
    | 'water-flow'
    | 'user'
    | 'logout'
}

export function AppIcon({
  name,
}: AppIconProps) {
  const commonProps = {
    width: 20,
    height: 20,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap:
      'round' as const,
    strokeLinejoin:
      'round' as const,
    'aria-hidden':
      true as const,
  }

  switch (name) {
    case 'dashboard':
      return (
        <svg {...commonProps}>
          <rect
            x="3"
            y="3"
            width="7"
            height="7"
            rx="2"
          />
          <rect
            x="14"
            y="3"
            width="7"
            height="7"
            rx="2"
          />
          <rect
            x="3"
            y="14"
            width="7"
            height="7"
            rx="2"
          />
          <rect
            x="14"
            y="14"
            width="7"
            height="7"
            rx="2"
          />
        </svg>
      )

    case 'sensors':
      return (
        <svg {...commonProps}>
          <path d="M12 3v10" />
          <path d="M8.5 13a5 5 0 1 0 7 0" />
          <circle
            cx="12"
            cy="17"
            r="1.5"
          />
        </svg>
      )

    case 'actuators':
      return (
        <svg {...commonProps}>
          <path d="M12 2v5" />
          <path d="M5.6 5.6a9 9 0 1 0 12.8 0" />
        </svg>
      )

    case 'feeding':
      return (
        <svg {...commonProps}>
          <path d="M4 7h16" />
          <path d="M6 7l1 13h10l1-13" />
          <path d="M9 3h6" />
          <path d="M10 11h4" />
        </svg>
      )

    case 'water-flow':
      return (
        <svg {...commonProps}>
          <path d="M3 7h10a4 4 0 0 1 4 4v2" />
          <path d="m13 11 4 4 4-4" />
          <path d="M21 17H11a4 4 0 0 1-4-4v-2" />
          <path d="m11 13-4-4-4 4" />
        </svg>
      )

    case 'refill':
      return (
        <svg {...commonProps}>
          <path d="M12 3s6 6.2 6 11a6 6 0 0 1-12 0c0-4.8 6-11 6-11Z" />
          <path d="M9.5 15.5c.7 1 1.5 1.5 2.5 1.5" />
        </svg>
      )

    case 'automation':
      return (
        <svg {...commonProps}>
          <path d="M8 4h8" />
          <path d="M8 20h8" />
          <circle
            cx="12"
            cy="12"
            r="3"
          />
          <path d="M12 9V4" />
          <path d="M12 15v5" />
          <path d="M9 12H4" />
          <path d="M20 12h-5" />
        </svg>
      )

    case 'alerts':
      return (
        <svg {...commonProps}>
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
          <path d="M10 21h4" />
        </svg>
      )

    case 'settings':
      return (
        <svg {...commonProps}>
          <circle
            cx="12"
            cy="12"
            r="3"
          />
          <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.1A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3v-4h.1A1.7 1.7 0 0 0 4.6 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3h4v.1A1.7 1.7 0 0 0 15.4 4a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.4.3.8.5 1.3.5h.3v4h-.3c-.5 0-.9.2-1.3.5Z" />
        </svg>
      )

    case 'user':
      return (
        <svg {...commonProps}>
          <circle
            cx="12"
            cy="8"
            r="4"
          />
          <path d="M4 21a8 8 0 0 1 16 0" />
        </svg>
      )

    case 'logout':
      return (
        <svg {...commonProps}>
          <path d="M10 17l5-5-5-5" />
          <path d="M15 12H3" />
          <path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" />
        </svg>
      )
  }
}