isEmpty(PREFIX){
    PREFIX = /usr
}

target.path = $${PREFIX}/bin/

desktop_files.path = $${PREFIX}/share/applications/
desktop_files.files = $$PWD/*.desktop

#services.path = $${PREFIX}/share/dbus-1/services
#services.files = $$PWD/data/*.service

dman.path = $${PREFIX}/share/dman/
dman.files = $$PWD/dman/*

translations.path = $${PREFIX}/share/$${TARGET}/translations
translations.files = $$PWD/translations/*.qm \
                     $$PWD/translations/desktop/*.qm

hicolor.path =  $${PREFIX}/share/icons/hicolor/scalable/apps
hicolor.files = $$PWD/resource/icons/logo.svg

INSTALLS += target translations desktop_files hicolor dman

GitVersion = $$system(git rev-parse HEAD)
DEFINES += GIT_VERSION=\\\"$$GitVersion\\\"

