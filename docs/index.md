---
layout: default
title: Home
nav_order: 1
---

<style>
.hero-section {
  margin: 2rem 0 3rem 0;
  padding: 2rem;
  background: var(--jtd-body-bg);
  border: 1px solid var(--jtd-border);
  border-radius: 8px;
}

.hero-section h1 {
  color: var(--jtd-accent);
  margin-bottom: 1rem;
  font-size: 2.5rem;
  font-weight: 600;
}

.hero-section p {
  font-size: 1.1rem;
  color: var(--jtd-primary-text);
  margin-bottom: 2rem;
  line-height: 1.5;
}

.cta-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.cta-button {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: var(--jtd-accent);
  color: var(--jtd-body-bg) !important;
  text-decoration: none;
  border-radius: 4px;
  font-weight: 500;
  transition: opacity 0.2s ease;
}

.cta-button:hover {
  opacity: 0.9;
}

.cta-button.secondary {
  background: transparent;
  border: 1px solid var(--jtd-accent);
  color: var(--jtd-accent) !important;
}

.cta-button.secondary:hover {
  background: var(--jtd-accent);
  color: var(--jtd-body-bg) !important;
}

@media (max-width: 768px) {
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
  <h1>gitfetch</h1>
  <p>A neofetch-style CLI tool for GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut statistics</p>
  <div class="cta-buttons">
    <a href="/gitfetch/installation.html" class="cta-button">Install</a>
    <a href="/gitfetch/gallery.html" class="cta-button secondary">Gallery</a>
    <a href="https://github.com/Matars/gitfetch" class="cta-button secondary">GitHub</a>
  </div>
</div>

> **Note**: This project is still maturing with only ~20 closed issues as of October 26, 2025. If you encounter bugs, have feature requests, or want to contribute, please [open an issue](https://github.com/Matars/gitfetch/issues) on GitHub!
