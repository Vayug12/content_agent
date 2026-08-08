# Design System

## Philosophy

This app follows a premium, minimal design language inspired by:

- ChatGPT
- Apple Human Interface Guidelines
- Linear
- Notion

The interface should feel calm, modern, intelligent, and effortless.

Never use flashy gradients, heavy shadows, oversized icons, or excessive colors.

The UI should prioritize whitespace, typography, hierarchy, and subtle animations over decoration.

---

# Core Principles

1. Less is more.
2. Every element must have a purpose.
3. Prefer whitespace over borders.
4. Avoid visual clutter.
5. Use smooth motion, never distracting animations.
6. Everything should feel premium.

---

# Color System

## Background

Primary Background
#FFFFFF

Secondary Background
#F7F7F8

Surface
#FFFFFF

Card
#FFFFFF

Divider
#ECECEC

---

## Text

Primary
#111111

Secondary
#666666

Muted
#8A8A8A

Disabled
#BDBDBD

---

## Accent

Primary Accent
#10A37F

Hover
#0D8C6B

Success
#10A37F

Warning
#F5A623

Danger
#E5484D

Never use multiple accent colors in one screen.

---

# Corner Radius

Buttons
14px

Cards
18px

Dialogs
20px

Bottom Sheets
28px

Input Fields
14px

Images
16px

---

# Shadows

Avoid heavy shadows.

Use extremely soft elevation.

Example

0 2 12 rgba(0,0,0,0.05)

or

0 4 20 rgba(0,0,0,0.04)

---

# Typography

Use Inter.

Weights

Regular 400

Medium 500

SemiBold 600

Bold 700

Never use more than four font sizes on one screen.

Display
32

Title
24

Heading
20

Body
16

Caption
14

Small
12

Line height should always feel spacious.

---

# Spacing

Use an 8-point grid.

Allowed spacing

4

8

12

16

20

24

32

40

48

64

Never invent random spacing values.

---

# Buttons

Primary

Filled

Green accent

White text

Height

52px

Radius

14px

Secondary

White background

Gray border

Dark text

Text Button

No border

Accent text

Never use gradients.

---

# Inputs

Height

52px

Rounded corners

14px

Soft gray background

No hard borders.

Focus should use the accent color.

---

# Cards

Cards should:

have lots of padding

soft corners

minimal shadow

no unnecessary outlines

avoid multiple nested cards

---

# Icons

Use Lucide icons.

Size

20 or 24

Stroke width

2

Never mix icon styles.

---

# Lists

Generous vertical spacing.

Each item should breathe.

Avoid dense layouts.

---

# Navigation

Bottom navigation should be simple.

No floating colorful effects.

Active item uses accent color.

Inactive items use muted gray.

---

# Animations

Duration

200–300ms

Use easeInOut.

Use fade, scale, or slide.

Never bounce.

Never over animate.

---

# Images

Rounded corners.

Consistent aspect ratios.

No decorative frames.

---

# Empty States

Every empty state should include:

simple illustration or icon

clear title

one sentence

primary action

---

# Loading

Prefer skeleton loading.

Avoid full-screen spinners.

---

# Error States

Explain the problem simply.

Offer one clear action.

---

# Accessibility

Minimum touch target

44x44

Contrast should remain high.

Support dynamic text.

---

# Screen Layout

Every screen follows:

Top App Bar

↓

Page Title

↓

Optional Description

↓

Primary Content

↓

Secondary Content

↓

Primary CTA

Use generous whitespace between sections.

---

# DO

✓ Minimal

✓ Premium

✓ Calm

✓ Spacious

✓ Consistent

✓ Apple quality

✓ ChatGPT style

✓ Linear style

✓ Professional

---

# DON'T

✗ Glassmorphism

✗ Neon colors

✗ Heavy gradients

✗ Large drop shadows

✗ Rounded blobs everywhere

✗ Material 3 colorful defaults

✗ Inconsistent spacing

✗ Different button styles

✗ Random font sizes

✗ Crowded layouts

---

# AI Instructions

Whenever creating a new screen:

- Reuse existing components whenever possible.
- Maintain identical spacing patterns.
- Do not invent new colors.
- Follow the typography scale.
- Keep interfaces minimal.
- Optimize for readability first.
- Every screen should look like it belongs in the same product.
- If unsure, choose the simpler option.
- The result should resemble a premium Apple-quality productivity app with the calm visual language of ChatGPT.