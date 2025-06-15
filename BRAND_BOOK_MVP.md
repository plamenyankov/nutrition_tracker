# VitaSync Brand Book (MVP)
## Quick Reference Design System

### 🎨 Essential Colors

```css
/* Primary Gradient - Use as main background */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Core Colors */
--primary: #007bff;
--success: #28a745;
--danger: #dc3545;
--warning: #ffc107;
--dark: #343a40;
--muted: #6c757d;
```

### 📐 Core Layout Rules

1. **Page Structure**
   ```html
   <div class="min-vh-100" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
       <!-- Content -->
   </div>
   ```

2. **Cards** (All content goes in cards)
   ```css
   background: white;
   border-radius: 16px;
   box-shadow: 0 4px 20px rgba(0,0,0,0.1);
   padding: 1.5rem;
   ```

3. **Sticky Header**
   ```css
   background: rgba(255, 255, 255, 0.95);
   backdrop-filter: blur(10px);
   position: sticky;
   top: 0;
   ```

### 🎯 Essential Components

#### Primary Button
```html
<button class="btn" style="
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 25px;
    font-weight: 600;
">Button Text</button>
```

#### Stat Card
```html
<div style="
    background: linear-gradient(135deg, #ff6b6b, #ee5a52);
    color: white;
    padding: 1.5rem;
    border-radius: 16px;
    text-align: center;
">
    <h3 style="font-size: 1.8rem; font-weight: 700;">123</h3>
    <small style="opacity: 0.8;">Label</small>
</div>
```

#### Form Input
```html
<input type="text" style="
    border-radius: 12px;
    border: 1px solid #dee2e6;
    padding: 0.75rem 1rem;
    width: 100%;
">
```

### 📱 Mobile-First Grid

```css
/* Default: Single column */
display: grid;
grid-template-columns: 1fr;
gap: 1rem;

/* Tablet+ : 2 columns */
@media (min-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
}

/* Desktop: 4 columns */
@media (min-width: 1024px) {
    grid-template-columns: repeat(4, 1fr);
}
```

### ✨ Key Interactions

1. **Hover Effect** (Cards & Buttons)
   ```css
   transition: all 0.3s ease;
   :hover {
       transform: translateY(-2px);
       box-shadow: 0 8px 30px rgba(0,0,0,0.15);
   }
   ```

2. **Focus State** (Inputs)
   ```css
   :focus {
       border-color: #667eea;
       box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
   }
   ```

### 🔤 Typography

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Sizes */
Hero: 2.5rem
Title: 1.75rem
Section: 1.3rem
Body: 1rem
Small: 0.85rem

/* Weights */
Bold: 700 (titles)
Semibold: 600 (buttons)
Regular: 400 (body)
```

### 🎭 Common Gradients

```css
/* Nutrition/Success */
background: linear-gradient(135deg, #4ecdc4, #44a08d);

/* Energy/Calories */
background: linear-gradient(135deg, #ff6b6b, #ee5a52);

/* Carbs/Warning */
background: linear-gradient(135deg, #ffeaa7, #fdcb6e);

/* Protein/Info */
background: linear-gradient(135deg, #a29bfe, #6c5ce7);
```

### 📋 Quick Checklist

- [ ] Purple gradient background on main container
- [ ] White cards with 16px border radius
- [ ] 0.3s ease transitions on interactive elements
- [ ] Mobile-first responsive grid
- [ ] Sticky header with backdrop blur
- [ ] Touch targets minimum 44x44px
- [ ] Consistent padding: 1.5rem for cards

### 🚀 Copy-Paste Template

```html
<div class="min-vh-100" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
    <!-- Sticky Header -->
    <div class="sticky-top" style="background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 1rem;">
        <h1 class="text-center fw-bold">Page Title</h1>
    </div>

    <!-- Content Container -->
    <div class="container py-4" style="max-width: 1200px;">
        <!-- Card -->
        <div style="background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); padding: 1.5rem; margin-bottom: 1rem;">
            <!-- Your content here -->
        </div>
    </div>
</div>
```
