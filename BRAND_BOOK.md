# VitaSync Brand Book
## UI/UX Design System Guide

### 🎨 Core Design Principles

#### 1. **Modern Gradient-First Design**
- Primary gradient background: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- Creates a vibrant, modern feel across all pages
- Used as the main background for the entire application

#### 2. **Card-Based Layout**
- All content organized in cards with rounded corners
- Consistent shadow and hover effects
- White background with subtle shadows for depth

#### 3. **Mobile-First Responsive**
- Optimized for mobile devices first
- Fluid layouts that adapt to larger screens
- Touch-friendly interface elements

---

### 🎨 Color Palette

#### Primary Colors
```css
--primary-color: #007bff;
--primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

#### Semantic Colors
```css
--success-color: #28a745;
--warning-color: #ffc107;
--danger-color: #dc3545;
--info-color: #17a2b8;
--dark-color: #343a40;
--light-color: #f8f9fa;
```

#### Gradient Combinations
```css
/* Nutrition/Success */
linear-gradient(135deg, #28a745 0%, #20c997 100%)
linear-gradient(135deg, #4ecdc4, #44a08d)

/* Energy/Warning */
linear-gradient(135deg, #ffeaa7, #fdcb6e)
linear-gradient(135deg, #ff6b6b, #ee5a52)

/* Info/Primary */
linear-gradient(135deg, #667eea, #764ba2)
linear-gradient(135deg, #a29bfe, #6c5ce7)

/* Gym/Activity */
linear-gradient(135deg, #dc3545 0%, #fd7e14 100%)
linear-gradient(135deg, #ff7675, #e84393)
```

---

### 📐 Layout & Spacing

#### Container Widths
- Mobile: 100% with 1rem padding
- Tablet: max-width: 800px
- Desktop: max-width: 1200px
- Content cards: max-width: 1200px centered

#### Border Radius
```css
--border-radius: 16px;  /* Primary cards */
--border-radius-sm: 12px;  /* Secondary elements */
--border-radius-lg: 20px;  /* Feature cards */
--border-radius-pill: 25px;  /* Buttons */
```

#### Shadows
```css
--shadow: 0 4px 20px rgba(0,0,0,0.1);
--shadow-sm: 0 2px 10px rgba(0,0,0,0.1);
--shadow-lg: 0 8px 30px rgba(0,0,0,0.15);
```

---

### 🔤 Typography

#### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

#### Font Sizes
- Hero Title: 2.5rem (mobile: 2rem)
- Page Title: 1.75rem
- Section Title: 1.5rem
- Card Title: 1.3rem
- Body Text: 1rem
- Small Text: 0.85rem
- Labels: 0.8rem

#### Font Weights
- Bold: 700-800 (titles)
- Semibold: 600 (buttons, important text)
- Regular: 400-500 (body text)

---

### 🎯 Component Patterns

#### 1. **Hero Sections**
```css
.hero-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem 1rem;
    text-align: center;
}
```
- Gradient background with white text
- Centered content with stats display
- Animated patterns for visual interest

#### 2. **Cards**
```css
.card {
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.15);
}
```

#### 3. **Buttons**

**Primary Button**
```css
.btn-primary {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 25px;
    font-weight: 600;
    transition: all 0.3s ease;
}
```

**Button States**
- Hover: `transform: translateY(-1px)` with enhanced shadow
- Active: Slightly darker gradient
- Disabled: Opacity 0.6

#### 4. **Form Elements**
```css
.form-control {
    border-radius: 12px;
    border: 1px solid #dee2e6;
    padding: 0.75rem 1rem;
    transition: all 0.3s ease;
}

.form-control:focus {
    border-color: #667eea;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
}
```

#### 5. **Navigation Headers**
- Sticky positioning with backdrop blur
- White background with 95% opacity
- Date navigation with chevron buttons
- Centered title with subtitle

---

### 📱 Mobile Patterns

#### Touch-Friendly Elements
- Minimum touch target: 44x44px
- Button padding: 0.75rem minimum
- Adequate spacing between interactive elements

#### Responsive Grid
```css
/* Mobile First */
grid-template-columns: 1fr;

/* Tablet */
@media (min-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
}

/* Desktop */
@media (min-width: 1024px) {
    grid-template-columns: repeat(4, 1fr);
}
```

---

### ✨ Interaction Patterns

#### 1. **Hover Effects**
- Cards: Lift with shadow enhancement
- Buttons: Slight lift with shadow
- Links: Color transition
- List items: Background color change

#### 2. **Transitions**
```css
transition: all 0.3s ease;
```
- Consistent 0.3s duration
- Ease timing function
- Applied to all interactive elements

#### 3. **Loading States**
- Spinner with primary color
- Centered in container
- Accompanying loading text

#### 4. **Empty States**
- Large icon (3-4rem)
- Descriptive title
- Helper text
- Call-to-action button

---

### 🎭 Icon Usage

#### Icon Libraries
- Font Awesome 5+ for general icons
- Bootstrap Icons for UI elements

#### Common Icons
- 🥗 Food/Nutrition: apple-alt, utensils, egg
- 🏋️ Gym/Exercise: dumbbell, running, heartbeat
- 📊 Analytics: chart-line, chart-bar
- 🤖 AI Assistant: robot, brain
- ➕ Add/Create: plus, plus-circle
- 📅 Calendar/Date: calendar, calendar-check
- 🔥 Calories: fire, burn
- ⚡ Energy/Protein: lightning, battery

---

### 📊 Data Visualization

#### Stat Cards
```css
.stat-card {
    background: linear-gradient(135deg, [color1], [color2]);
    color: white;
    text-align: center;
    padding: 1.5rem;
    border-radius: 16px;
}
```

#### Progress Indicators
- Circular progress for percentages
- Bar charts for comparisons
- Line charts for trends

---

### 🔧 Utility Classes

#### Spacing
- `.p-{1-5}`: Padding (0.25rem - 3rem)
- `.m-{1-5}`: Margin (0.25rem - 3rem)
- `.g-{1-5}`: Grid gap (0.25rem - 3rem)

#### Text
- `.text-center`: Center alignment
- `.fw-bold`: Font weight 700
- `.text-muted`: Gray color (#6c757d)

#### Display
- `.d-flex`: Flexbox container
- `.d-grid`: Grid container
- `.d-none`: Hidden element

---

### 📋 Implementation Checklist

When creating new pages, ensure:

- [ ] Gradient background applied to body/main container
- [ ] Content wrapped in white cards with shadows
- [ ] Consistent border radius (16px for cards)
- [ ] Hover effects on interactive elements
- [ ] Mobile-responsive grid layouts
- [ ] Touch-friendly button sizes
- [ ] Proper spacing between elements
- [ ] Loading and empty states
- [ ] Smooth transitions (0.3s ease)
- [ ] Accessible color contrasts

---

### 🚀 Quick Start Template

```html
<!-- Page Container -->
<div class="min-vh-100" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">

    <!-- Header -->
    <div class="sticky-top" style="background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);">
        <div class="container py-3">
            <h1 class="text-center fw-bold">Page Title</h1>
        </div>
    </div>

    <!-- Content -->
    <div class="container py-4">
        <!-- Card -->
        <div class="card border-0 shadow-sm mb-4" style="border-radius: 16px;">
            <div class="card-body p-4">
                <!-- Card content -->
            </div>
        </div>
    </div>
</div>
```

---

This brand book provides the essential design patterns and guidelines for maintaining consistency across the VitaSync nutrition tracker application. Follow these patterns when creating new features or pages to ensure a cohesive user experience.
