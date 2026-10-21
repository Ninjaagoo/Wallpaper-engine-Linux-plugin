// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: page
    twinFormLayouts: parentLayout

    property alias cfg_command: command.text
    property alias cfg_allowInput: allowInput.checked
    property alias cfg_unscaled: unscaled.checked
    property alias cfg_socket: socket.text
    property alias cfg_fps: fps.value

    property string sockettext: cfg_socket

    TextField {
        id: command
        Kirigami.FormData.label: i18n("Application to run:")
        placeholderText: i18n("Command")
    }

    SpinBox {
        Kirigami.FormData.label: i18n("FPS limit:")
        id: fps
        from: 0
        to: 9999999
        stepSize: 1
        live: true
        textFromValue: (value, locale) => value ? value : i18n("off")
        valueFromText: (text, locale) => text == i18n("off") ? 0 : Number.fromLocaleString(locale, text)
    }

    RowLayout {
        Kirigami.FormData.label: i18n("Advanced settings:")
        CheckBox {
            id: allowInput
            text: i18n("Pass input events")
        }

        Kirigami.ContextualHelpButton {
            toolTipText: i18n("Input events (pointer & keyboard) can only be passed through the desktop wallpaper. This option is ineffective on the screen locker.")
        }
    }

    CheckBox {
        id: unscaled
        text: i18n("Disable HiDPI scaling")
    }

    RowLayout {
        CheckBox {
            id: customSocket
            text: i18n("Use custom Wayland socket name")
            onCheckedChanged: {
                if (!checked) {
                    sockettext = socket.text
                    socket.text = ""
                } else {
                    socket.text = sockettext
                }
            }
        }

        Kirigami.ContextualHelpButton {
            toolTipText: i18n("Requires a reload to take effect. Don't use on the lock screen with multiple outputs.")
        }
    }

    TextField {
        id: socket
        placeholderText: i18n("Socket")
        visible: customSocket.checked
        onTextChanged: {
            if (text) {
                customSocket.checked = true
                sockettext = text
            }
        }
        validator: RegularExpressionValidator { regularExpression: /^[A-Za-z0-9._-]+$/ }
    }
}
