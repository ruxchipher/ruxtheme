/* ruxtheme - a Quick Settings entry for switching the desktop theme.
 *
 * The heavy lifting lives in ~/.local/bin/ruxtheme; this is just a front end.
 * Clicking the icon opens the carousel, the arrow opens a menu of every theme,
 * and the subtitle always shows what is live.
 */

import GObject from 'gi://GObject';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {QuickMenuToggle, SystemIndicator} from 'resource:///org/gnome/shell/ui/quickSettings.js';

const HOME = GLib.get_home_dir();
const PAL = `${HOME}/.config/ruxtheme/palettes`;
const CUR = `${HOME}/.config/ruxtheme/current`;
const BIN = `${HOME}/.local/bin/ruxtheme`;
const CAROUSEL = `${HOME}/.local/bin/ruxtheme-carousel`;

function readText(path) {
    try {
        const [ok, bytes] = GLib.file_get_contents(path);
        if (!ok)
            return null;
        return new TextDecoder().decode(bytes);
    } catch {
        return null;
    }
}

/** Every palette, as {name, label, order}, sorted the same way `ruxtheme list` sorts. */
function listThemes() {
    const out = [];
    let dir;
    try {
        dir = Gio.File.new_for_path(PAL).enumerate_children(
            'standard::name', Gio.FileQueryInfoFlags.NONE, null);
    } catch {
        return out;
    }
    let info;
    while ((info = dir.next_file(null)) !== null) {
        const fn = info.get_name();
        if (!fn.endsWith('.env'))
            continue;
        const name = fn.slice(0, -4);
        const body = readText(`${PAL}/${fn}`) ?? '';
        const label = (body.match(/^ct_label='(.*)'$/m) ?? [null, name])[1];
        const order = parseInt((body.match(/^ct_order=(\d+)$/m) ?? [null, '99'])[1], 10);
        out.push({name, label, order});
    }
    dir.close(null);
    out.sort((a, b) => a.order - b.order);
    return out;
}

function currentTheme() {
    return (readText(CUR) ?? '').trim();
}

function spawn(argv) {
    try {
        new Gio.Subprocess({argv, flags: Gio.SubprocessFlags.NONE}).init(null);
    } catch (e) {
        logError(e, 'ruxtheme: failed to spawn');
    }
}

const RuxToggle = GObject.registerClass(
class RuxToggle extends QuickMenuToggle {
    _init() {
        super._init({
            title: 'Theme',
            iconName: 'preferences-desktop-theme-symbolic',
            toggleMode: false,
        });

        this.menu.setHeader('preferences-desktop-theme-symbolic', 'Desktop theme',
            'ruxchipher');

        this._section = new PopupMenu.PopupMenuSection();
        this.menu.addMenuItem(this._section);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const carousel = new PopupMenu.PopupMenuItem('Open carousel…');
        carousel.connect('activate', () => {
            Main.panel.closeQuickSettings();
            spawn([CAROUSEL]);
        });
        this.menu.addMenuItem(carousel);

        // clicking the tile itself opens the carousel too
        this.connect('clicked', () => {
            Main.panel.closeQuickSettings();
            spawn([CAROUSEL]);
        });

        // keep the subtitle honest if the theme changes from the CLI
        this._monitor = Gio.File.new_for_path(CUR).monitor_file(
            Gio.FileMonitorFlags.NONE, null);
        this._monitorId = this._monitor.connect('changed', () => this._refresh());

        this.menu.connect('open-state-changed', (_m, open) => {
            if (open)
                this._refresh();
        });

        this._refresh();
    }

    _refresh() {
        const live = currentTheme();
        const themes = listThemes();
        const hit = themes.find(t => t.name === live);
        this.subtitle = hit ? hit.label : 'unknown';
        this.checked = !!hit;

        this._section.removeAll();
        for (const t of themes) {
            const item = new PopupMenu.PopupImageMenuItem(
                t.label, t.name === live ? 'object-select-symbolic' : '');
            item.connect('activate', () => {
                Main.panel.closeQuickSettings();
                spawn([BIN, 'set', t.name]);
            });
            this._section.addMenuItem(item);
        }
    }

    destroy() {
        if (this._monitor) {
            if (this._monitorId)
                this._monitor.disconnect(this._monitorId);
            this._monitor.cancel();
            this._monitor = null;
            this._monitorId = null;
        }
        super.destroy();
    }
});

const RuxIndicator = GObject.registerClass(
class RuxIndicator extends SystemIndicator {
    _init() {
        super._init();
        this.quickSettingsItems.push(new RuxToggle());
    }
});

export default class RuxThemeExtension extends Extension {
    enable() {
        this._indicator = new RuxIndicator();
        Main.panel.statusArea.quickSettings.addExternalIndicator(this._indicator);
    }

    disable() {
        this._indicator?.quickSettingsItems.forEach(i => i.destroy());
        this._indicator?.destroy();
        this._indicator = null;
    }
}
