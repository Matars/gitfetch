---
layout: default
title: Gallery
nav_order: 9
---

<style>
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
}

.gallery-item {
  border: 1px solid var(--jtd-border);
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  background: var(--jtd-page-bg);
}

.gallery-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(138, 180, 248, 0.15);
}

.gallery-item img {
  width: 100%;
  height: auto;
  display: block;
  transition: transform 0.2s ease;
}

.gallery-item:hover img {
  transform: scale(1.02);
}

.gallery-caption {
  padding: 1rem;
  background: var(--jtd-body-bg);
  border-top: 1px solid var(--jtd-border);
}

.gallery-caption h3 {
  margin: 0 0 0.5rem 0;
  color: var(--jtd-accent);
  font-size: 1.1rem;
}

.gallery-caption p {
  margin: 0;
  color: var(--jtd-muted-text);
  font-size: 0.9rem;
}

.hero-section {
  margin: 2rem 0 3rem 0;
  padding: 2rem;
  background: linear-gradient(135deg, var(--jtd-body-bg) 0%, rgba(138, 180, 248, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--jtd-border);
}

.hero-section h1 {
  color: var(--jtd-accent);
  margin-bottom: 1rem;
  font-size: 2.5rem;
}

.hero-section p {
  font-size: 1.2rem;
  color: var(--jtd-primary-text);
  margin-bottom: 1.5rem;
}

.cta-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.cta-button {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #22c55e;
  background-color: #333;
  color: white !important;
  text-decoration: none;
  border-radius: 4px;
  font-weight: 500;
}

.contribute-section {
  margin: 3rem 0;
  padding: 2rem;
  background: var(--jtd-body-bg);
  border: 1px solid var(--jtd-border);
  border-radius: 8px;
}

.contribute-section h2 {
  color: var(--jtd-accent);
  margin-bottom: 1rem;
}

@media (max-width: 768px) {
  .gallery-grid {
    grid-template-columns: 1fr;
  }

  .hero-section h1 {
    font-size: 2rem;
  }

  .hero-section p {
    font-size: 1rem;
  }

  .cta-buttons {
    flex-direction: column;
  }
}
</style>

<div class="hero-section">
  <h1>Community Gallery</h1>
  <p>Showcase your beautiful terminal setups and get inspired by the community</p>
  <div class="cta-buttons">
    <a href="/gitfetch/contributing.html" class="cta-button">Contribute Your Setup</a>
    <a href="https://github.com/Matars/gitfetch" class="cta-button">View on GitHub</a>
  </div>
</div>

## Community Setups Gallery

<div class="gallery-grid">
  <div class="gallery-item">
    <img width="3024" height="1964" alt="Default gitfetch display with GitHub stats" src="https://github.com/user-attachments/assets/bbb18d5d-4787-4998-a352-e8f4e59642c0" />
    <div class="gallery-caption">
      <h3>Classic GitHub Setup</h3>
      <p>Default gitfetch display showing comprehensive GitHub statistics with the classic three layouts</p>
    </div>
  </div>

  <div class="gallery-item">
    <img width="3012" height="1982" alt="Minimal gitfetch configuration" src="https://github.com/user-attachments/assets/6d061c76-3e45-47c3-989f-0776be6cf846" />
    <div class="gallery-caption">
      <h3>Modified Configuration</h3>
      <p>These setups use the visual flags feature to enhance their appearance. Here we have examples of ``--no-(component)``, ``--custom-box``</p>
    </div>
  </div>

  <div class="gallery-item">
    <img width="3441" height="1441" alt="Custom themed gitfetch with Hyprland" src="https://github.com/user-attachments/assets/ee31ebe3-257f-4aff-994e-fffd47b48fa1" />
    <div class="gallery-caption">
      <h3>Hyprland Integration</h3>
      <p>Beautiful integration with Hyprland window manager by <a href="https://github.com/fwtwoo">@fwtwoo</a></p>
    </div>
  </div>
</div>

<div class="contribute-section">
  <h2>Share Your Setup</h2>
  <p>Have a beautiful gitfetch setup? We'd love to feature it in our gallery!</p>

  <h3>How to Contribute</h3>
  <ol>
    <li><strong>Customize your setup</strong> - Use gitfetch's extensive configuration options</li>
    <li><strong>Take a screenshot</strong> - Capture your terminal with gitfetch running</li>
    <li><strong>Create an issue</strong> - Open a GitHub issue with your screenshot and configuration details</li>
    <li><strong>Get featured</strong> - Your setup might be added to our gallery!</li>
  </ol>
  <p><a href="/gitfetch/contributing.html" class="cta-button">Learn More About Contributing</a></p>
</div>
