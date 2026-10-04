{
  description = "İzlek — Linux için yerel film ve dizi takibi";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      eachSystem = nixpkgs.lib.genAttrs systems;
      packageFor = system:
        let pkgs = import nixpkgs { inherit system; };
        in pkgs.callPackage ./packaging/nix/package.nix { };
    in {
      packages = eachSystem (system: {
        izlek = packageFor system;
        default = self.packages.${system}.izlek;
      });

      apps = eachSystem (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.izlek}/bin/izlek";
        };
      });

      checks = eachSystem (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          package = self.packages.${system}.izlek;
          smoke = pkgs.runCommand "izlek-installed-smoke" {
            nativeBuildInputs = [ self.packages.${system}.izlek ];
          } ''
            export QT_QPA_PLATFORM=offscreen
            export QT_QUICK_BACKEND=software
            export XDG_CONFIG_HOME="$TMPDIR/config"
            export XDG_DATA_HOME="$TMPDIR/data"
            export XDG_CACHE_HOME="$TMPDIR/cache"
            export XDG_STATE_HOME="$TMPDIR/state"
            izlek --package-smoke-test
            test -f "$XDG_DATA_HOME/izlek/izlek.sqlite3"
            test -f "$XDG_CONFIG_HOME/izlek/window.ini"
            touch "$out"
          '';
        });
    };
}
