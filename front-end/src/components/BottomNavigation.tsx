import './BottomNavigation.css'

interface BottomNavigationProps {
  currentScreen: string
  onScreenChange: (screen: string) => void
}

const BottomNavigation = ({ currentScreen, onScreenChange }: BottomNavigationProps) => {
  const navItems = [
    { id: 'profile-check', icon: '/Профиль.png', label: 'Проверить' },
    { id: 'pricing', icon: '/Тарифы.png', label: 'Тарифы' },
    { id: 'info', icon: '/Инфо.png', label: 'Инфо' },
  ]

  return (
    <nav className="bottom-navigation">
      {navItems.map(item => (
        <button
          key={item.id}
          className={`nav-item ${currentScreen === item.id ? 'active' : ''}`}
          onClick={() => onScreenChange(item.id)}
        >
          <img width={50} src={item.icon} alt={item.label} className="nav-icon" />
          <span className="nav-label">{item.label}</span>
        </button>
      ))}
    </nav>
  )
}

export default BottomNavigation 