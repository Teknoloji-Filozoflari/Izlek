{
  lib,
  python3,
  qt6,
  ruff,
  makeFontsConf,
  dejavu_fonts,
}:
let
  project = builtins.fromTOML (builtins.readFile ../../pyproject.toml);
  fonts = makeFontsConf { fontDirectories = [ dejavu_fonts ]; };
in
python3.pkgs.buildPythonApplication {
  pname = "izlek";
  version = project.project.version;
  pyproject = true;

  # Exclude developer environments, generated binaries and local databases.
  src = lib.cleanSourceWith {
    src = ../..;
    filter = path: type:
      let name = baseNameOf path;
      in lib.cleanSourceFilter path type
        && !(builtins.elem name [
          ".venv" ".pytest_cache" ".ruff_cache" "__pycache__"
          "build" "dist" "parts" "stage" "prime" ".snapcraft" "result"
        ])
        && !(lib.hasSuffix ".egg-info" name)
        && !(lib.hasPrefix "result-" name)
        && !(lib.hasSuffix ".pyc" name)
        && !(lib.hasSuffix ".sqlite3" name)
        && !(lib.hasSuffix ".sqlite" name)
        && !(lib.hasPrefix ".env" name);
  };

  build-system = [ python3.pkgs.setuptools ];
  dependencies = with python3.pkgs; [
    pyside6 sqlalchemy alembic httpx pydantic keyring
  ];
  nativeBuildInputs = [ qt6.wrapQtAppsHook ];
  buildInputs = with qt6; [ qtbase qtdeclarative qtsvg qtwayland ];

  # Merge the Qt plugin/QML environment into the Python entry point wrapper.
  dontWrapQtApps = true;
  preFixup = ''
    makeWrapperArgs+=( "''${qtWrapperArgs[@]}" )
    makeWrapperArgs+=( --set FONTCONFIG_FILE "${fonts}" )
  '';

  nativeCheckInputs = [ python3.pkgs.pytest python3.pkgs.pygobject3 ruff ];
  checkPhase = ''
    runHook preCheck
    export QT_QPA_PLATFORM=offscreen
    export QT_QUICK_BACKEND=software
    export FONTCONFIG_FILE="${fonts}"
    export QT_PLUGIN_PATH="${qt6.qtbase}/${qt6.qtbase.qtPluginPrefix}:${qt6.qtsvg}/${qt6.qtbase.qtPluginPrefix}"
    export QML2_IMPORT_PATH="${qt6.qtdeclarative}/${qt6.qtbase.qtQmlPrefix}"
    export XDG_CONFIG_HOME="$TMPDIR/config"
    export XDG_DATA_HOME="$TMPDIR/data"
    export XDG_CACHE_HOME="$TMPDIR/cache"
    export XDG_STATE_HOME="$TMPDIR/state"
    ruff check .
    ${python3.interpreter} -m pytest -q
    runHook postCheck
  '';

  postInstall = ''
    install -Dm644 src/izlek/resources/desktop/izlek.desktop \
      "$out/share/applications/izlek.desktop"
    install -Dm644 src/izlek/resources/icons/izlek.svg \
      "$out/share/icons/hicolor/scalable/apps/izlek.svg"
  '';
  pythonImportsCheck = [ "izlek" "izlek.app" ];

  meta = {
    description = "Local-first film and TV tracking desktop application";
    homepage = "https://github.com/Teknoloji-Filozoflari/Izlek";
    license = lib.licenses.gpl3Plus;
    platforms = lib.platforms.linux;
    mainProgram = "izlek";
  };
}
