/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
  	extend: {
  		opacity: Object.fromEntries(Array.from({ length: 101 }, (_, i) => [i, `${i / 100}`])),
  		borderRadius: { lg: 'var(--radius)', md: 'calc(var(--radius) - 2px)', sm: 'calc(var(--radius) - 4px)' },
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
  			popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
  			primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
  			secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
  			muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
  			accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
  			destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: { '1':'hsl(var(--chart-1))','2':'hsl(var(--chart-2))','3':'hsl(var(--chart-3))','4':'hsl(var(--chart-4))','5':'hsl(var(--chart-5))' },
  			sidebar: {
  				DEFAULT: 'hsl(var(--sidebar-background))', foreground: 'hsl(var(--sidebar-foreground))',
  				primary: 'hsl(var(--sidebar-primary))', 'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
  				accent: 'hsl(var(--sidebar-accent))', 'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
  				border: 'hsl(var(--sidebar-border))', ring: 'hsl(var(--sidebar-ring))'
  			},
  			ink: '#061410',
  			panel: '#122A20',
  			recess: '#0A1812',
  			hairline: '#1B3D2F',
  			ivory: '#F5F0E6',
  			dust: '#A8B5A0',
  			quiet: '#5C6E60',
  			land: '#F5F0E6',
  			mapland: '#D5D9DE',
  			hill: '#B8BEC6',
  			street: '#F0E6B8',
  			highway: '#1A1A1A',
  			arterial: '#2C2C2C',
  			mapwater: '#4A90D9',
  			maplabel: '#3D3D3D',
  			road: '#FFFFFF',
  			'road-edge': '#0D1F18',
  			building: '#D4CBB8',
  			water: '#4A90D9',
  			park: '#A8B5A0',
  			tunnel: '#0D1F18',
  			route: '#E6B800',
  			gnss: '#2E5A3C',
  			ins: '#E6B800',
  			blackout: '#C62828',
  			match: '#3D5C45',
  			forest: '#3D5C45'
  		},
  		fontFamily: {
  			display: ['Teko', 'sans-serif'],
  			sans: ['Overpass', 'sans-serif'],
  			heading: ['Overpass', 'sans-serif'],
  			body: ['Overpass', 'sans-serif'],
  			mono: ['Overpass Mono', 'monospace']
  		},
  		keyframes: {
  			'accordion-down': { from: { height: '0' }, to: { height: 'var(--radix-accordion-content-height)' } },
  			'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: '0' } }
  		},
  		animation: { 'accordion-down': 'accordion-down 0.2s ease-out', 'accordion-up': 'accordion-up 0.2s ease-out' }
  	}
  },
  plugins: [require("tailwindcss-animate")],
}
