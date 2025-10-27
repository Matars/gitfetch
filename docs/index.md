---
layout: default
title: Home
nav_order: 1
---

<style>
.hero-section {
  text-align: center;
  margin: 2rem 0 3rem 0;
  padding: 3rem 2rem;
  background: linear-gradient(135deg, var(--jtd-body-bg) 0%, rgba(138, 180, 248, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--jtd-border);
}

.hero-section h1 {
  color: var(--jtd-accent);
  margin-bottom: 1rem;
  font-size: 3rem;
  font-weight: 700;
}

.hero-section p {
  font-size: 1.3rem;
  color: var(--jtd-primary-text);
  margin-bottom: 2rem;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}

.cta-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.cta-button {
  display: inline-block;
  padding: 0.875rem 2rem;
  background: var(--jtd-accent);
  color: var(--jtd-body-bg) !important;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 1.1rem;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(138, 180, 248, 0.2);
}

.cta-button:hover {
  background: #9bb5f9;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(138, 180, 248, 0.4);
}

.cta-button.secondary {
  background: transparent;
  border: 2px solid var(--jtd-accent);
  color: var(--jtd-accent) !important;
}

.cta-button.secondary:hover {
  background: var(--jtd-accent);
  color: var(--jtd-body-bg) !important;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin: 3rem 0;
}

.feature-card {
  padding: 2rem;
  background: var(--jtd-page-bg);
  border: 1px solid var(--jtd-border);
  border-radius: 8px;
  text-align: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.feature-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(138, 180, 248, 0.1);
}

.feature-card h3 {
  color: var(--jtd-accent);
  margin-bottom: 1rem;
  font-size: 1.3rem;
}

.feature-card p {
  color: var(--jtd-muted-text);
  line-height: 1.6;
}

.quick-start {
  background: var(--jtd-body-bg);
  border: 1px solid var(--jtd-border);
  border-radius: 8px;
  padding: 2rem;
  margin: 3rem 0;
}

.quick-start h2 {
  color: var(--jtd-accent);
  text-align: center;
  margin-bottom: 2rem;
}

.code-block {
  background: #0b0c0d;
  border: 1px solid var(--jtd-border);
  border-radius: 6px;
  padding: 1.5rem;
  margin: 1rem 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9rem;
  overflow-x: auto;
}

@media (max-width: 768px) {
  .hero-section h1 {
    font-size: 2.5rem;
  }

  .hero-section p {
    font-size: 1.2rem;
  }

  .cta-buttons {
    flex-direction: column;
    align-items: center;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<div class="hero-section">
  <h1>gitfetch</h1>
  <p>A beautiful, neofetch-style CLI tool for displaying your GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut statistics in the terminal</p>
  <div class="cta-buttons">
    <a href="/gitfetch/installation.html" class="cta-button">Get Started</a>
    <a href="/gitfetch/gallery.html" class="cta-button secondary">View Gallery</a>
    <a href="https://github.com/Matars/gitfetch" class="cta-button secondary">GitHub</a>
  </div>
</div>

> **Note**: This project is still maturing with only ~20 closed issues as of October 26, 2025. If you encounter bugs, have feature requests, or want to contribute, please [open an issue](https://github.com/Matars/gitfetch/issues) on GitHub!

## Quick Start

<div class="quick-start">
  <h2>Get Up and Running</h2>

  <h3>Install gitfetch</h3>
  <div class="code-block">
pip install git+https://github.com/Matars/gitfetch
  </div>

  <h3>Run with your GitHub username</h3>
  <div class="code-block">
gitfetch --username your-github-username
  </div>

  <h3>Or configure for multiple providers</h3>
  <div class="code-block">
gitfetch --config
  </div>
</div>

## Features

<div class="features-grid">
  <div class="feature-card">
    <h3>Multi-Platform Support</h3>
    <p>Works with GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut. Display statistics from all your favorite git hosting platforms.</p>
  </div>

  <div class="feature-card">
    <h3>Highly Customizable</h3>
    <p>Extensive configuration options for colors, layouts, and display preferences. Make it look exactly how you want it to.</p>
  </div>

  <div class="feature-card">
    <h3>Rich Statistics</h3>
    <p>Comprehensive stats including commits, PRs, issues, stars, followers, and more. Get insights into your development activity.</p>
  </div>

  <div class="feature-card">
    <h3>Fast & Efficient</h3>
    <p>SQLite-based caching ensures quick subsequent runs. No more waiting for API calls on every execution.</p>
  </div>

  <div class="feature-card">
    <h3>Cross-Platform</h3>
    <p>Works seamlessly on macOS, Linux, and Windows. Your terminal companion wherever you code.</p>
  </div>

  <div class="feature-card">
    <h3>Neofetch-Style</h3>
    <p>Familiar interface inspired by neofetch. Perfect for system information enthusiasts and terminal lovers.</p>
  </div>
</div>

## Explore More

- [Installation Guide](/gitfetch/installation.html) - Detailed setup instructions
- [Configuration](/gitfetch/configuration.html) - Customize your gitfetch experience
- [Community Gallery](/gitfetch/gallery.html) - See amazing setups from the community
- [Contributing](/gitfetch/contributing.html) - Join the development effort
- [Usage Examples](/gitfetch/usage.html) - Learn all the features
