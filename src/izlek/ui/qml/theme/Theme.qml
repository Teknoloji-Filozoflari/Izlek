pragma Singleton
import QtQuick

QtObject {
    property string mode: "dark"
    readonly property bool isLight: mode === "light"

    // Dark palette tracks Diziler mock: muted teal-green charcoal, soft teal accents.
    readonly property color background: isLight ? "#EEF1F5" : "#0B1F22"
    readonly property color surface: isLight ? "#FFFFFF" : "#122A2E"
    readonly property color surfaceElevated: isLight ? "#F4F7FB" : "#1A3539"
    readonly property color border: isLight ? "#D0D8E2" : "#2C484C"
    readonly property color textPrimary: isLight ? "#15202B" : "#F3FAF9"
    readonly property color textSecondary: isLight ? "#4A5A6D" : "#A7B9BC"
    readonly property color textMuted: isLight ? "#748396" : "#7F9497"
    readonly property color accent: isLight ? "#1A8F7A" : "#5EC4B4"
    readonly property color success: isLight ? "#2F9B6A" : "#78C59B"
    readonly property color warning: isLight ? "#C4881C" : "#E5B869"
    readonly property color danger: isLight ? "#C24B55" : "#F0353C"
    readonly property color accentText: isLight ? "#F4FFFB" : "#06201C"
    readonly property color accentSurface: isLight ? "#D7F0EA" : "#1B3F3D"
    readonly property color successSurface: isLight ? "#DCF0E5" : "#243C32"
    readonly property color warningSurface: isLight ? "#F7ECD4" : "#423623"
    readonly property color dangerSurface: isLight ? "#F5DDE0" : "#3F2528"
    readonly property color hoverSurface: isLight ? "#E4EAF1" : "#243E42"
    readonly property color skeleton: isLight ? "#D8DFE8" : "#2A4347"
    readonly property color scrim: isLight ? "#B8EEF1F5" : "#B80B1F22"
    readonly property color statsAccent: isLight ? "#C99712" : "#FFCC45"
    readonly property color statsAccentText: isLight ? "#FFF8E8" : "#241D0C"
    readonly property color chartBlue: isLight ? "#3F6FBF" : "#5B83D7"

    readonly property int spaceXs: 6
    readonly property int spaceSm: 10
    readonly property int spaceMd: 16
    readonly property int spaceLg: 24
    readonly property int spaceXl: 32
    readonly property int space2xl: 40
    readonly property int radiusSm: 8
    readonly property int radiusMd: 14
    readonly property int radiusLg: 20
    readonly property int textSmall: 12
    readonly property int textBody: 14
    readonly property int textEmpty: 18
    readonly property int textBrand: 20
    readonly property int textHeading: 24
    readonly property int textStat: 28
    readonly property int weightMedium: Font.Medium
    readonly property int weightDemiBold: Font.DemiBold
    readonly property int animationFast: 120
    readonly property int animationNormal: 180
    readonly property int sidebarExpanded: 228
    readonly property int sidebarCompact: 68
    readonly property int cardWidth: 164
    readonly property int cardCompactWidth: 142
    readonly property int posterHeight: 246
    readonly property int cardTitleHeight: 40
    readonly property int cardInfoHeight: 90
    readonly property int cardHeight: posterHeight + cardInfoHeight
    readonly property int gridGap: 14
    readonly property int controlHeight: 42
}
