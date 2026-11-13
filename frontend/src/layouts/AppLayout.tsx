import {
  NavLink,
  Outlet,
} from 'react-router-dom'

import {
  AppIcon,
} from '../components/common/AppIcon'
import {
  ConnectionStatus,
} from '../components/common/ConnectionStatus'
import { env } from '../config/env'
import { useAuth } from '../hooks/useAuth'


type NavigationIcon =
  | 'dashboard'
  | 'sensors'
  | 'feeding'
  | 'alerts'
  | 'settings'
  | 'water-flow'


interface NavigationItem {
  label: string
  path: string
  icon: NavigationIcon
  end?: boolean
}


const navigationItems:
  readonly NavigationItem[] = [
    {
      label: 'Dashboard',
      path: '/',
      icon: 'dashboard',
      end: true,
    },
    {
      label: 'Sensors',
      path: '/sensors',
      icon: 'sensors',
    },
    {
      label: 'Feeding',
      path: '/feeding',
      icon: 'feeding',
    },
    {
      label: 'Water Flow',
      path: '/water-flow',
      icon: 'water-flow',
    },
    {
      label: 'Alerts',
      path: '/alerts',
      icon: 'alerts',
    },
    {
      label: 'Settings',
      path: '/settings',
      icon: 'settings',
    },
  ]


export function AppLayout() {
  const auth = useAuth()

  const username =
    auth.user?.username ?? 'User'

  const initial =
    username
      .charAt(0)
      .toUpperCase()

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <div
            className="sidebar-brand__mark"
            aria-hidden="true"
          >
            <span className="sidebar-brand__leaf">
              ◒
            </span>
          </div>

          <div className="sidebar-brand__text">
            <span className="sidebar-brand__name">
              {env.appTitle}
            </span>

            <span className="sidebar-brand__subtitle">
              Smart Aquaponics
            </span>
          </div>
        </div>

        <div className="sidebar-section-label">
          Management
        </div>

        <nav
          className="primary-navigation"
          aria-label="Primary navigation"
        >
          {navigationItems.map(
            ({
              label,
              path,
              icon,
              end,
            }) => (
              <NavLink
                key={path}
                to={path}
                end={end}
                className={({
                  isActive,
                }) =>
                  [
                    'navigation-link',
                    isActive
                      ? 'navigation-link--active'
                      : '',
                  ]
                    .filter(Boolean)
                    .join(' ')
                }
              >
                <span className="navigation-link__icon">
                  <AppIcon
                    name={icon}
                  />
                </span>

                <span>
                  {label}
                </span>
              </NavLink>
            ),
          )}
        </nav>

        <div className="sidebar-account">
          <div
            className="sidebar-account__avatar"
            aria-hidden="true"
          >
            {initial}
          </div>

          <div className="sidebar-account__identity">
            <span className="sidebar-account__username">
              {username}
            </span>

            <span className="sidebar-account__role">
              Administrator
            </span>
          </div>
        </div>
      </aside>

      <div className="app-workspace">
        <header className="app-topbar">
          <div className="app-topbar__heading">
            <span className="app-topbar__context">
              AquaMind Aquaponics Center
            </span>

            <span className="app-topbar__title">
              Smart Aquaponics Monitoring
            </span>
          </div>

          <div className="app-topbar__actions">
            <ConnectionStatus />

            <div className="app-user">
              <div
                className="app-user__avatar"
                aria-hidden="true"
              >
                {initial}
              </div>

              <div className="app-user__identity">
                <span className="app-user__name">
                  {username}
                </span>

                <span className="app-user__role">
                  Admin
                </span>
              </div>

              <button
                type="button"
                className="app-logout"
                onClick={() => {
                  void auth.logout()
                }}
              >
                <AppIcon
                  name="logout"
                />

                <span>
                  Sign out
                </span>
              </button>
            </div>
          </div>
        </header>

        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}