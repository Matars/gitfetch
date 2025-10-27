let
  flake-compat = import (builtins.fetchTarball {
    url = "https://github.com/edolstra/flake-compat/archive/master.tar.gz";
  }) { src = ./.; };
  system = builtins.currentSystem;
in
  flake-compat.defaultNix.packages.${system}.default
