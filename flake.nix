{
  description = "Python 3.13 development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;
        pythonPackages = python.pkgs;

        myPackage = pythonPackages.buildPythonPackage {
          pname = "gitfetch";
          version = "1.2.6";
          src = ./.;
          
          # Main dependencies
          propagatedBuildInputs = with pythonPackages; [
            requests
            readchar
            setuptools
          ];

          # Dependencies for testing
          nativeCheckInputs = with pythonPackages; [
            pytest
          ];

          # Disable tests when building
          doCheck = false;
          
          format = "pyproject";
        };
      in
      {
        # nix build
        packages.default = myPackage;

        # nix run
        apps.default = {
          type = "app";
          program = "${myPackage}/bin/gitfetch";
        };
      }
    );
}
