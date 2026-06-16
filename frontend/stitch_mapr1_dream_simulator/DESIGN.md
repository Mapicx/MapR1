---
name: Cyber-Tactical Green
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#bccabb'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#869486'
  outline-variant: '#3d4a3e'
  surface-tint: '#4de082'
  primary: '#6bfb9a'
  on-primary: '#003919'
  primary-container: '#4ade80'
  on-primary-container: '#005e2d'
  inverse-primary: '#006d36'
  secondary: '#c8c6c5'
  on-secondary: '#313030'
  secondary-container: '#474746'
  on-secondary-container: '#b7b5b4'
  tertiary: '#ffd9c1'
  on-tertiary: '#4f2500'
  tertiary-container: '#ffb47f'
  on-tertiary-container: '#794418'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6dfe9c'
  primary-fixed-dim: '#4de082'
  on-primary-fixed: '#00210c'
  on-primary-fixed-variant: '#005227'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c5'
  on-secondary-fixed: '#1c1b1b'
  on-secondary-fixed-variant: '#474746'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb784'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#6c3a0f'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.05em
  label-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.1em
spacing:
  unit: 4px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
  container-max-width: 1280px
---

## Brand & Style

This design system embodies a high-performance, "Cyber-Tactical" aesthetic designed for precision, data density, and technical authority. The personality is focused, nocturnal, and alert, evoking the feel of a heads-up display (HUD) or a secure terminal interface.

The design style is a hybrid of **Minimalism** and **Tactile Futurism**. It strips away decorative fluff in favor of structural clarity while utilizing light as a functional material. Instead of soft blurs, the system uses sharp neon accents and rhythmic patterns (scanlines and grids) to create a sense of active monitoring and digital depth. The UI should feel like a high-contrast command center—engineered rather than decorated.

## Colors

The palette is strictly nocturnal, anchored by "Obsidian" blacks to maximize the impact of the high-visibility neon green accent.

- **Primary (#4ade80):** A high-energy neon green used for critical actions, active states, and data highlights. It represents "system active" status.
- **Surface Layer 1 (#0a0a0a):** The base obsidian canvas. Pure, deep charcoal with zero blue saturation.
- **Surface Layer 2 (#1a1a1a):** A secondary elevation for cards and containers, providing subtle contrast against the base.
- **Borders:** Thin, high-contrast outlines using the Primary green at varying opacities (100% for active, 30% for inactive).
- **Background Texture:** A subtle, repeating 20px grid or horizontal scanline pattern (1px height) in #1a1a1a is applied to the base layer to reinforce the tactical digital environment.

## Typography

The typographic strategy balances the modern readability of **Inter** with the technical, "machine-read" aesthetic of **JetBrains Mono**.

- **Primary Sans (Inter):** Used for all primary communication, headlines, and body copy. It ensures that despite the aggressive styling, the interface remains highly legible and professional.
- **Data Mono (JetBrains Mono):** Used for all numerical data, status labels, timestamps, and metadata. This font should always be set in uppercase for labels to enhance the "tactical" feel.
- **Emphasis:** High-contrast weight shifts are preferred over color shifts for hierarchy. Use Bold weights for primary navigation and Medium weights for data points.

## Layout & Spacing

The layout is built on a rigid 4px baseline grid, ensuring all elements align with mathematical precision. 

- **Grid Model:** Use a 12-column fluid grid for desktop with 16px gutters. Elements should feel "locked" into the grid.
- **Density:** High information density is encouraged. Padding should be compact to allow for multiple data streams to be visible simultaneously.
- **Reflow:** On mobile, margins shrink to 16px and the grid collapses to a single column. All interactive elements must maintain a minimum 44px hit area despite the compact visual styling.

## Elevation & Depth

This system rejects soft shadows and blurs. Depth is achieved through **Tonal Layering** and **Luminescent Outlines**.

- **Stacked Surfaces:** Secondary surfaces (#1a1a1a) sit visually "above" the obsidian base (#0a0a0a).
- **Glow Effects:** Instead of drop shadows, use `box-shadow` with 0 blur and a 1px spread of the primary neon green to indicate focus or "active" elevation.
- **Visual Scaffolding:** Use a subtle, glowing 1px green border for high-priority containers. Inactive containers use a dim grey border (#333333).
- **Tactile Overlays:** Apply a persistent, low-opacity (5%) horizontal scanline overlay across the entire viewport to simulate a screen-based terminal.

## Shapes

The shape language is strictly **Sharp (0px)**. 

Every UI element—from buttons to cards to input fields—must have 90-degree corners. This reinforces the "Tactical/Industrial" theme and ensures the UI feels like a precision-milled instrument. In rare cases where a distinction is needed (e.g., status pips), use perfect squares or 45-degree chamfered corners rather than radius-based rounding.

## Components

- **Buttons:** Sharp edges, 1px solid neon green border. On hover, the background fills with a 10% opacity green tint. Text is always uppercase JetBrains Mono.
- **Input Fields:** Obsidian background with a 1px bottom-border only (#333333). On focus, the border becomes neon green and spans the full perimeter.
- **Status Chips:** Small square indicators. Use solid neon green for "Active," hollow green for "Standby," and a flickering red (#ff4b4b) for "Critical."
- **Cards:** No shadows. Use a 1px #1a1a1a border. Add a small "corner bracket" detail in neon green to the top-left and bottom-right corners to emphasize the HUD aesthetic.
- **Data Lists:** Zebra-striping using #0a0a0a and #121212. Use JetBrains Mono for all list values to maintain alignment in columns.
- **Scanlines/Grids:** Apply a CSS-generated grid pattern to the main content area to serve as a visual anchor for data-heavy dashboards.