---
layout: default
title: Installation
nav_order: 3
---

# Installation

gitfetch can be installed on macOS and Linux without any prerequisites. During first-run setup, you'll be guided to install and authenticate with the necessary CLI tools or provide access tokens for your chosen git hosting platform.

## macOS (Homebrew)

```bash
brew tap matars/gitfetch
brew install gitfetch
```

## Arch Linux (AUR)

```bash
yay -S gitfetch-python
```

Or with other AUR helpers:

```bash
paru -S gitfetch-python
trizen -S gitfetch-python
```

Or manual build:

```bash
git clone https://aur.archlinux.org/gitfetch-python.git
cd gitfetch-python
makepkg -si
```

## NixOS (Flake only)

### Installation:

To install, you should add an input to your flake:
```nix
gitfetch.url = "github:Matars/gitfetch";
```

Minimal flake variant for it to work:
```nix
{
  description = "My awesome flake";

	inputs = {
	  nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05"; # or your version
	  gitfetch.url = "github:Matars/gitfetch";
	};
  outputs = inputs@{ self, nixpkgs, gitfetch }:
  	let
  		system = "x86_64-linux";
  		pkgs = import nixpkgs { 
  		  inherit system; 
  		};
  	in {
  	  nixosConfigurations = {
  	  	nixos = nixpkgs.lib.nixosSystem {
  	  	  specialArgs = { inherit system; inherit inputs; };
		  modules = [
		    ./configuration.nix
		  ];
  	  	};
  	  };
  	};
}
```

Then in ``environment.systemPackages`` add this:
```nix
environment.systemPackages = with pkgs; [
	# ...
	inputs.gitfetch.packages.${system}.default # your actual input name
	gh # don't forget to install it and authenticate
]
```

### Updating

To update, run these commands and then rebuild
```shell
nix flake update gitfetch # gitfetch should be replaced by your input name in the flake
nixos-rebuild switch
```

## From Source

### With pip

```bash
git clone https://github.com/Matars/gitfetch.git
cd gitfetch
pip install -e .
```

### With uv

```bash
uv tool install git+https://github.com/Matars/gitfetch
```

### With pipx

```bash
pipx install git+https://github.com/Matars/gitfetch
```

## First-run Setup

When you run `gitfetch` for the first time, you'll be prompted to:

1. **Choose your git hosting provider** (GitHub, GitLab, Gitea/Forgejo/Codeberg, or Sourcehut)
2. **Install required CLI tools** (if using GitHub or GitLab)
3. **Authenticate** with your chosen platform
4. **Configure access tokens** (if using Gitea/Forgejo/Codeberg or Sourcehut)

The setup process will provide helpful error messages and installation instructions if anything is missing.

## Uninstall

### Homebrew

```bash
brew uninstall gitfetch          # Uninstall gitfetch
brew untap matars/gitfetch       # Remove the tap
```

### pip

```bash
pip uninstall gitfetch
```

### uv

```bash
uv tool uninstall gitfetch
```

### pipx

```bash
pipx uninstall gitfetch
```

### AUR (Arch Linux)

```bash
yay -R gitfetch-python
```

Or with other AUR helpers:

```bash
paru -R gitfetch-python
trizen -R gitfetch-python
```

### NixOS

Remove the gitfetch input from your flake and remove it from `environment.systemPackages`.
