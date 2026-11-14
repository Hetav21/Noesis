{
  description = "Noesis development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      vercel-cli = pkgs.writeShellScriptBin "vercel" ''
        exec ${pkgs.nodejs_22}/bin/npx --yes vercel "$@"
      '';
      vc-cli = pkgs.writeShellScriptBin "vc" ''
        exec ${pkgs.nodejs_22}/bin/npx --yes vercel "$@"
      '';
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          python311
          uv
          nodejs_22
          bun
          playwright-driver.browsers
          render-cli
          vercel-cli
          vc-cli
        ];

        shellHook = ''
          export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
          export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
          export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]}:''${LD_LIBRARY_PATH:-}"
          echo "Noesis development environment loaded"
        '';
      };
    };
}
