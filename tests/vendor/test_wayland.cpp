#include <QtTest>
#include <QTest>
#include <QTestEventList>
#include <QDebug>
#include <QAbstractButton>
#include <DSettingsDialog>
#include <dwidgetstype.h>

#include <unistd.h>
#include <gtest/gtest.h>

#include "application.h"
#include "dmr_settings.h"
#include "utils.h"
#include "movie_configuration.h"
#include "dbus_adpator.h"

using namespace dmr;
using namespace utils;

TEST(Wayland, wayland)
{
    MainWindow *w = dApp->getMainWindow();
    w->close();
    delete w;
    w = nullptr;

    qputenv("QT_WAYLAND_SHELL_INTEGRATION", "kwayland-shell");
    //qputenv("_d_disableDBusFileDialog", "true");
    setenv("PULSE_PROP_media.role", "video", 1);
    QSurfaceFormat format;
    format.setRenderableType(QSurfaceFormat::OpenGLES);
    format.setDefaultFormat(format);
    utils::set_wayland(true);
    bool iswayland = utils::first_check_wayland_env();

    MainWindow *w_wayland = new MainWindow;
    auto &mc = MovieConfiguration::get();
    MovieConfiguration::get().init();
    PlayerEngine *engine =  w_wayland->engine();
    ToolboxProxy *toolboxProxy = w_wayland->toolbox();
    ToolButton *listBtn = toolboxProxy->listBtn();
    ToolButton *fsBtn = toolboxProxy->fsBtn();
    ButtonBoxButton* playBtn = static_cast<ButtonBoxButton *>(toolboxProxy->playBtn());
    ButtonBoxButton* nextBtn = static_cast<ButtonBoxButton *>(toolboxProxy->nextBtn());
    ButtonBoxButton* prevBtn = static_cast<ButtonBoxButton *>(toolboxProxy->prevBtn());
    QList<QUrl> listPlayFiles;
    listPlayFiles << QUrl::fromLocalFile("/data/source/deepin-movie-reborn/movie/demo.mp4")\
                  << QUrl::fromLocalFile("/data/source/deepin-movie-reborn/movie/bensound-sunny.mp3");
    const auto &valids = engine->addPlayFiles(listPlayFiles);
    QTest::qWait(200);
    w_wayland->show();

#if !defined (__mips__ ) && !defined(__aarch64__)
    Settings::get().settings()->setOption("base.play.showInthumbnailmode", true);
    qDebug() << __func__ << Settings::get().settings()->option("base.play.showInthumbnailmode");
#endif

    Settings::get().settings()->setOption("base.play.resumelast", false);
    qDebug() << Settings::get().settings()->option("base.play.resumelast");

    if(!valids.empty()){
//        QTest::mouseMove(playBtn, QPoint(), 100);
//        QTest::mouseClick(playBtn, Qt::LeftButton, Qt::NoModifier, QPoint(), 500); //play

        QTest::qWait(200);
        const auto &valids = engine->addPlayFiles(listPlayFiles);
        engine->playByName(valids[0]);

        w_wayland->requestAction(ActionFactory::ActionKind::ToggleMute);
        QTest::qWait(200);
        QTest::mouseMove(fsBtn, QPoint(), 200);
        QTest::mouseClick(fsBtn, Qt::LeftButton, Qt::NoModifier, QPoint(), 500);
        QTest::mouseMove(listBtn, QPoint(), 200);
        QTest::mouseClick(listBtn, Qt::LeftButton, Qt::NoModifier,QPoint(), 500);
        fsBtn->showToolTip();

        QTest::mouseMove(nextBtn, QPoint(), 200);
        QTest::mouseClick(nextBtn, Qt::LeftButton, Qt::NoModifier, QPoint(), 500); //play next
        QTest::qWait(200);
//    DGuiApplicationHelper::instance()->setThemeType(DGuiApplicationHelper::DarkType);
//    emit DGuiApplicationHelper::instance()->paletteTypeChanged(DGuiApplicationHelper::DarkType);
        QTest::mouseMove(prevBtn, QPoint(), 200);
        QTest::mouseClick(prevBtn, Qt::LeftButton, Qt::NoModifier, QPoint(), 500); //play prev

        QTest::mouseMove(listBtn, QPoint(), 200);
        QTest::mouseClick(listBtn, Qt::LeftButton, Qt::NoModifier, QPoint(), 500);
        QTest::mouseMove(fsBtn, QPoint(), 200);
        QTest::mouseClick(fsBtn, Qt::LeftButton, Qt::NoModifier, QPoint(), 500);

        Settings::get().settings()->setOption("base.play.emptylist", false);
    }
    ApplicationAdaptor *appAdaptor = new ApplicationAdaptor(w_wayland);
    appAdaptor->Raise();
    appAdaptor->openFile("/data/source/deepin-movie-reborn/movie/demo.mp4");
    QStringList fileList;
    fileList << "/data/source/deepin-movie-reborn/movie/demo.mp4"\
             <<"/data/source/deepin-movie-reborn/movie/bensound-sunny.mp3";
    appAdaptor->openFiles(fileList);


    QEvent enterEvent(QEvent::Enter);
    QEvent leaveEvent(QEvent::Leave);
    QApplication::sendEvent(playBtn, &enterEvent);
    QApplication::sendEvent(playBtn, &leaveEvent);
    QApplication::sendEvent(fsBtn, &enterEvent);
    QApplication::sendEvent(fsBtn, &leaveEvent);


#if !defined (__mips__ ) && !defined(__aarch64__)
    Settings::get().settings()->setOption("base.play.showInthumbnailmode", false);
#endif
    Settings::get().settings()->setOption("base.play.resumelast", true);
//    w_wayland->close();
    QTest::qWait(100);
    delete w_wayland;
    w_wayland = nullptr;
}
