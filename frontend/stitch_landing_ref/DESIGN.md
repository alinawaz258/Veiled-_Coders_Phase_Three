# Design System Specification: The Kinetic Minimalist

## 1. Overview & Creative North Star
**Creative North Star: "The Architectural Ledger"**

This design system rejects the cluttered, legacy aesthetic of traditional finance in favor of high-end editorial precision. We are building an experience that feels less like a banking app and more like a curated digital workspace for the modern professional. 

The "Architectural Ledger" approach prioritizes **Negative Space as Structure**. By removing borders and heavy shadows, we rely on a sophisticated hierarchy of typographic weight and tonal shifts. The interface should feel "expensive"—achieved not through decoration, but through the extreme intentionality of alignment, massive whitespace, and a high-contrast palette. We break the standard grid by using asymmetric "floating" layouts where content is anchored by heavy, brutalist headlines and balanced by the softness of pill-shaped interactive elements.

---

## 2. Colors & Tonal Depth
We utilize a sophisticated Material-based palette to manage depth. The core experience is driven by the interaction between the primary Teal (`#0d9488`) and a clinical Light Gray background.

### The "No-Line" Rule
**Explicit Instruction:** Designers are strictly prohibited from using 1px solid borders to define sections. Layout boundaries must be established solely through background color shifts.
*   **Primary Surface:** `surface` (#f9f9fb)
*   **Secondary Sectioning:** `surface-container-low` (#f3f3f5) or `surface-container` (#eeeef0)
*   **Example:** Use a `surface-container-highest` background for a sidebar to distinguish it from the `surface` main content area.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. To create depth without shadows:
1.  **Level 0 (Base):** `surface`
2.  **Level 1 (Sections):** `surface-container-low`
3.  **Level 2 (In-section Cards):** `surface-container-lowest` (pure white)
This "nesting" creates a soft, natural lift that mimics fine stationery layered on a desk.

### The "Glass & Soul" Rule
While the aesthetic is "flat," we avoid a "dead" look by using **Glassmorphism** for floating navigation bars or contextual overlays.
*   **Token:** Use `surface` at 80% opacity with a `24px` backdrop-blur.
*   **Signature Texture:** For primary Action Cards, a subtle transition from `primary` (#00685f) to `primary_container` (#008378) is permitted to provide a "lit from within" premium feel.

---

## 3. Typography
The typography is the voice of the brand: authoritative, precise, and unwavering. We use **Inter** exclusively.

*   **Display & Headlines:** Weight 800 (Extra Bold). Tracking: `-0.04em`. These should feel dense and powerful. Use `headline-lg` for hero moments to anchor the vast amounts of whitespace.
*   **Body Copy:** Weight 400. Tracking: `normal`. High legibility is paramount.
*   **Labels:** Weight 600. Uppercase is encouraged for `label-sm` to create an "architectural blueprint" aesthetic.

| Level | Token | Size | Weight | Tracking |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | 3.5rem | 800 | -0.05em |
| **Headline**| `headline-md`| 1.75rem | 800 | -0.04em |
| **Title**   | `title-md`   | 1.125rem | 600 | -0.01em |
| **Body**    | `body-md`    | 0.875rem | 400 | 0 |
| **Label**   | `label-md`   | 0.75rem  | 600 | +0.02em |

---

## 4. Elevation & Depth
In this system, elevation is a function of light and tone, not lines.

*   **The Layering Principle:** Depth is achieved by "stacking" surface tiers. A `surface-container-lowest` card placed on a `surface-container-high` section creates a premium, tactile lift.
*   **Ambient Shadows:** If a component must "float" (e.g., a modal or a primary FAB), use a shadow with a `48px` blur and `4%` opacity, tinted with the `on-surface` color (#1a1c1d). This mimics natural, ambient room light.
*   **The "Ghost Border" Fallback:** If accessibility requires a container edge, use the `outline_variant` token at **15% opacity**. This creates a "suggestion" of a border rather than a hard line.

---

## 5. Components

### Buttons & Chips
*   **Primary Button:** Pill-shaped (`rounded-full`), `primary` background, `on_primary` text. No shadow.
*   **Secondary Button:** Pill-shaped, `surface-container-highest` background, `primary` text.
*   **Chips:** Used for filtering. `rounded-full`, 1.5rem height. Use `surface-container-high` for unselected and `primary` for selected.

### The Signature "72px" Icon Square
*   **Form:** All primary category icons must be housed in a 72px x 72px container with a `2rem` (lg) roundedness. 
*   **Styling:** Use `surface-container-low` for the background and `primary` for the icon glyph itself.

### Input Fields
*   **Style:** Minimalist underline or subtle background fill (`surface-container-low`). 
*   **Focus State:** Shift background to `surface-container-lowest` and add a 2px `primary` bottom indicator. No full-box strokes.

### Lists & Cards
*   **The No-Divider Rule:** Explicitly forbid 1px horizontal lines between list items. Use the **Spacing Scale** (`1.4rem` to `2rem`) to create separation. Content should be grouped by proximity, not by containment.

### Featured Component: The "Gig Ledger" Card
A specialized card for financial data. It uses `surface-container-lowest`, an `800` weight headline, and a `tertiary` (Amber) accent bar only when an alert is present.

---

## 6. Do’s and Don’ts

### Do
*   **Do** embrace extreme whitespace. If a layout feels "finished," add 20% more padding.
*   **Do** use `primary` (Teal) sparingly to draw the eye to the single most important action.
*   **Do** use `surface-container` shifts to create "zones" within a page.

### Don’t
*   **Don’t** use purple, gradients (outside of subtle CTA soul), or standard "card shadows."
*   **Don’t** use 1px borders to separate content. It breaks the "Architectural Ledger" flow.
*   **Don’t** use standard tracking on headlines. If it’s not "tight," it’s not this design system.
*   **Don’t** use center-alignment for long-form content. Stick to a sophisticated, left-aligned editorial grid.