// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

// Vuetify
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  components,
  directives,
  defaults: {
    global: {
      ripple: false,
    },
    VCard: {
      elevation: 0,
      variant: 'flat', // Use flat for cleaner look, we will add border manually or via class
      color: 'surface',
      rounded: 'lg',
    },
    VBtn: {
      rounded: 'lg',
      fontWeight: '600',
      letterSpacing: '0.5px',
      variant: 'flat' 
    },
    VTextField: {
      variant: 'outlined',
      color: 'primary',
      bgColor: 'rgba(15, 23, 42, 0.5)', // Slightly darker input background
    },
    VSelect: {
      variant: 'outlined',
      color: 'primary',
      bgColor: 'rgba(15, 23, 42, 0.5)',
    },
    VNavigationDrawer: {
      color: 'background',
      elevation: 0,
      border: 'none',
    },
    VAppBar: {
      color: 'background',
      elevation: 0,
    }
  },
  theme: {
    defaultTheme: 'deepOcean',
    themes: {
      deepOcean: {
        dark: true,
        colors: {
          background: '#020617', // Very dark slate (almost black blue)
          surface: '#1e293b',    // Slate 800
          'surface-light': '#334155', // Slate 700
          
          primary: '#818cf8',    // Indigo 400 (Brighter for dark mode)
          'primary-darken-1': '#6366f1',
          
          secondary: '#c084fc',  // Purple 400
          
          error: '#f87171',      // Red 400
          info: '#60a5fa',       // Blue 400
          success: '#34d399',    // Emerald 400
          warning: '#fbbf24',    // Amber 400
          
          'on-background': '#f1f5f9', // Slate 100
          'on-surface': '#f8fafc',    // Slate 50
        },
      },
    },
  },
})
