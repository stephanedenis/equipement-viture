# Viture XR Glasses - Linux Support

Configuration et outils pour utiliser les lunettes **Viture XR** comme écran stéréoscopique Side-by-Side (SBS) sous Linux.

## Matériel requis

- **Viture XR Glasses** (ou Viture Pro/Lite/One)
- **Viture HDMI XR Adapter** - Indispensable pour connecter à un PC
- Câble HDMI vers le port HDMI de l'adaptateur

## Configuration testée

| Élément | Détail |
|---------|--------|
| OS | openSUSE Tumbleweed |
| GPU | AMD Radeon (amdgpu) |
| Port | HDMI-1 |
| Adaptateur | Viture HDMI XR Adapter |

## Mode Side-by-Side (SBS)

Les lunettes Viture supportent le mode SBS où chaque œil voit une moitié de l'écran:
- **Œil gauche**: pixels 0-1919
- **Œil droit**: pixels 1920-3839

### Résolution recommandée

```
3840x1080 @ 60Hz (Reduced Blanking)
```

**Important**: Le mode "reduced blanking" est essentiel. Le mode standard à 346 MHz cause des artefacts visuels (jaune, ghosting). Le mode reduced blanking à 266.5 MHz fonctionne parfaitement.

## Installation rapide

```bash
# Cloner le repo
git clone https://github.com/stephanedenis/equipement-viture.git
cd equipement-viture

# Installer les règles udev (optionnel)
sudo cp linux/99-viture.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules

# Activer le mode SBS
./scripts/viture-sbs.sh on
```

## Utilisation manuelle

### Activer le mode SBS

```bash
# Créer le mode (si pas déjà existant)
xrandr --newmode "3840x1080R" 266.50 3840 3888 3920 4000 1080 1083 1093 1111 +hsync -vsync

# Ajouter le mode à HDMI-1
xrandr --addmode HDMI-1 "3840x1080R"

# Activer le mode
xrandr --output HDMI-1 --mode "3840x1080R"
```

### Revenir au mode normal

```bash
xrandr --output HDMI-1 --mode "1920x1080"
```

## Spécifications techniques du mode SBS

```
Modeline "3840x1080R":
  - Pixel Clock: 266.50 MHz (reduced blanking)
  - Horizontal: 3840 active, 3888 sync start, 3920 sync end, 4000 total
  - Vertical: 1080 active, 1083 sync start, 1093 sync end, 1111 total
  - Sync: +hsync -vsync
  - Refresh: ~60 Hz
```

### Pourquoi reduced blanking?

Le HDMI XR Adapter a des limites de bande passante. Le mode standard:
- **3840x1080 standard**: 346 MHz → Artefacts visuels
- **3840x1080R reduced**: 266.5 MHz → Parfait

## Tester avec du contenu 3D

### Vidéo SBS avec mpv

```bash
mpv --video-stereo-mode=sbs2l video_sbs.mp4
```

### VLC

1. Outils → Effets et filtres → Effets vidéo → Avancé
2. Cocher "Anaglyph 3D" ou utiliser le filtre SBS approprié

## Structure du repo

```
equipement-viture/
├── README.md           # Ce fichier
├── scripts/
│   └── viture-sbs.sh   # Script d'activation SBS
└── linux/
    └── 99-viture.rules # Règles udev
```

## Dépannage

### Les lunettes ne sont pas détectées

1. Vérifier que l'adaptateur HDMI XR est alimenté (LED)
2. `xrandr` doit montrer HDMI-1 comme connecté
3. Essayer un autre port HDMI ou un autre câble

### Artefacts visuels (jaune, ghosting)

Utiliser le mode reduced blanking (`3840x1080R`), pas le mode standard.

### L'image est inversée ou mal alignée

Vérifier l'orientation du mode SBS:
- `sbs2l` = gauche-droite (standard)
- `sbs2r` = droite-gauche (inversé)

## Voir aussi

- [Viture Official](https://www.viture.com/)
- [xrandr documentation](https://www.x.org/wiki/Projects/XRandR/)

## License

MIT License - Voir [LICENSE](LICENSE)
