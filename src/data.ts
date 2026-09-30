import type { WorldKind } from './world/worldMode'
import { worldKindOf } from './world/worldMode'

export const ACCENT = '#E0623A'

export const assets = {
  heroBg: '/assets/4b1402777bd373612f4d98819a7354b0.jpg',
  adam: '/assets/a16bb9f88fae0f272583b94b115782cc.webp',
  god: '/assets/65b03692fd1c9453919281969fe5882b.webp',
  heroOverlay: '/assets/cd49bb573d4ebf390f70eede40338e7f.webp',
  apple: '/assets/apple.png',
  buildVideo: '/assets/ba058a066e2dd9712c939f7917ef360c.mp4',
  buildPoster: '/assets/7f86a7afe3d220c80fd265a8d1158b6c.jpg',
  annunciation: '/assets/e88bde8eeb47d18c201850735b5aac9d.jpg',
  littaMadonna: '/assets/e47885471e0b63469289398c2834e424.jpg',
  cranach: '/assets/bcb5c4da75218934ee1ad20411fc17f3.jpg',
  pontormo: '/assets/0b549164f64db7a7fb9c821d4632589b.jpg',
  exploreVideo: '/assets/231d7a96cad8f1f4e90d172e4cc35076.mp4',
  explorePoster: '/assets/fc937389f7260fb497fcf5247a063da7.jpg',
  lutePlayer: '/assets/0f6682fccb74ec118bfeb9d5bec93460.jpg',
  parallax: {
    far: '/assets/parallax/1-far.webp',
    clouds: '/assets/parallax/2-clouds.webp',
    landscape: '/assets/parallax/3-landscape.webp',
    rock: '/assets/parallax/4-rock.webp',
    adam: '/assets/parallax/5-adam.webp',
    god: '/assets/parallax/6-god.webp',
  },
} as const

export type Curiosity = {
  id: number
  title: string
  text: string
  x: string
  y: string
  xMobile: string
  yMobile: string
}

export const curiosities: Curiosity[] = [
  {
    id: 1,
    title: 'A prophecy over her head',
    text: 'The Hebrew letters above the Virgin quote Isaiah 7:14: “Behold, a young woman shall conceive.”',
    x: '84%',
    y: '10.5%',
    xMobile: '88%',
    yMobile: '12%',
  },
  {
    id: 2,
    title: 'The painter’s home hills',
    text: 'Cima often set his scenes before the hills of his native Conegliano, in the Veneto.',
    x: '47.5%',
    y: '40%',
    xMobile: '46%',
    yMobile: '41%',
  },
  {
    id: 3,
    title: 'A flower with a message',
    text: 'The white lily Gabriel carries is a traditional symbol of Mary’s purity.',
    x: '46%',
    y: '57%',
    xMobile: '45%',
    yMobile: '59%',
  },
]

export type GalleryWork = {
  id: string
  /** When set, selecting this work opens the prepared explorable world. */
  worldId?: string
  title: string
  artist: string
  year: string
  src: string
  alt: string
  widthClass: string
}

export const galleryWorks: GalleryWork[] = [
  {
    id: 'school-of-athens',
    worldId: 'school-of-athens',
    title: 'The School of Athens',
    artist: 'Raphael',
    year: '1509–1511',
    src: '/data/paintings/school-of-athens/thumb.webp',
    alt: 'Raphael, The School of Athens',
    widthClass: 'wide',
  },
  {
    id: 'last-supper',
    worldId: 'last-supper',
    title: 'The Last Supper',
    artist: 'Leonardo da Vinci',
    year: '1495–1498',
    src: '/data/paintings/last-supper/thumb.webp',
    alt: 'Leonardo da Vinci, The Last Supper',
    widthClass: 'wide',
  },
  {
    id: 'arnolfini-portrait',
    worldId: 'arnolfini-portrait',
    title: 'The Arnolfini Portrait',
    artist: 'Jan van Eyck',
    year: '1434',
    src: '/data/paintings/arnolfini-portrait/thumb.webp',
    alt: 'Jan van Eyck, The Arnolfini Portrait',
    widthClass: 'narrow',
  },
  {
    id: 'wedding-at-cana',
    worldId: 'wedding-at-cana',
    title: 'The Wedding at Cana',
    artist: 'Paolo Veronese',
    year: '1563',
    src: '/data/paintings/wedding-at-cana/thumb.webp',
    alt: 'Paolo Veronese, The Wedding at Cana',
    widthClass: 'wide',
  },
  {
    id: 'harvesters',
    worldId: 'harvesters',
    title: 'The Harvesters',
    artist: 'Pieter Bruegel the Elder',
    year: '1565',
    src: '/data/paintings/harvesters/thumb.webp',
    alt: 'Pieter Bruegel the Elder, The Harvesters',
    widthClass: 'medium',
  },
  {
    id: 'ambassadors',
    worldId: 'ambassadors',
    title: 'The Ambassadors',
    artist: 'Hans Holbein the Younger',
    year: '1533',
    src: '/data/paintings/ambassadors/thumb.webp',
    alt: 'Hans Holbein the Younger, The Ambassadors',
    widthClass: 'medium',
  },
  {
    id: 'birth-of-venus',
    worldId: 'birth-of-venus',
    title: 'The Birth of Venus',
    artist: 'Sandro Botticelli',
    year: 'c. 1485',
    src: '/data/paintings/birth-of-venus/thumb.webp',
    alt: 'Sandro Botticelli, The Birth of Venus',
    widthClass: 'wide',
  },
  {
    id: 'primavera',
    worldId: 'primavera',
    title: 'Primavera',
    artist: 'Sandro Botticelli',
    year: 'c. 1482',
    src: '/data/paintings/primavera/thumb.webp',
    alt: 'Sandro Botticelli, Primavera',
    widthClass: 'wide',
  },
  {
    id: 'mona-lisa',
    worldId: 'mona-lisa',
    title: 'Mona Lisa',
    artist: 'Leonardo da Vinci',
    year: 'c. 1503–1506',
    src: '/data/paintings/mona-lisa/thumb.webp',
    alt: 'Leonardo da Vinci, Mona Lisa',
    widthClass: 'narrow',
  },
  {
    id: 'lady-with-an-ermine',
    worldId: 'lady-with-an-ermine',
    title: 'Lady with an Ermine',
    artist: 'Leonardo da Vinci',
    year: 'c. 1489–1491',
    src: '/data/paintings/lady-with-an-ermine/thumb.webp',
    alt: 'Leonardo da Vinci, Lady with an Ermine',
    widthClass: 'narrow',
  },
  {
    id: 'night-watch',
    worldId: 'night-watch',
    title: 'The Night Watch',
    artist: 'Rembrandt van Rijn',
    year: '1642',
    src: '/data/paintings/night-watch/thumb.webp',
    alt: 'Rembrandt van Rijn, The Night Watch',
    widthClass: 'wide',
  },
  {
    id: 'las-meninas',
    worldId: 'las-meninas',
    title: 'Las Meninas',
    artist: 'Diego Velázquez',
    year: '1656',
    src: '/data/paintings/las-meninas/thumb.webp',
    alt: 'Diego Velázquez, Las Meninas',
    widthClass: 'medium',
  },
  {
    id: 'girl-with-a-pearl-earring',
    worldId: 'girl-with-a-pearl-earring',
    title: 'Girl with a Pearl Earring',
    artist: 'Johannes Vermeer',
    year: 'c. 1665',
    src: '/data/paintings/girl-with-a-pearl-earring/thumb.webp',
    alt: 'Johannes Vermeer, Girl with a Pearl Earring',
    widthClass: 'narrow',
  },
  {
    id: 'garden-of-earthly-delights',
    worldId: 'garden-of-earthly-delights',
    title: 'The Garden of Earthly Delights',
    artist: 'Hieronymus Bosch',
    year: 'c. 1490–1500',
    src: '/data/paintings/garden-of-earthly-delights/thumb.webp',
    alt: 'Hieronymus Bosch, The Garden of Earthly Delights',
    widthClass: 'wide',
  },
  {
    id: 'creation-of-adam',
    worldId: 'creation-of-adam',
    title: 'The Creation of Adam',
    artist: 'Michelangelo',
    year: 'c. 1512',
    src: '/data/paintings/creation-of-adam/thumb.webp',
    alt: 'Michelangelo, The Creation of Adam',
    widthClass: 'wide',
  },
  {
    id: 'starry-night',
    worldId: 'starry-night',
    title: 'The Starry Night',
    artist: 'Vincent van Gogh',
    year: '1889',
    src: '/data/paintings/starry-night/thumb.webp',
    alt: 'Vincent van Gogh, The Starry Night',
    widthClass: 'wide',
  },
  {
    id: 'great-wave',
    worldId: 'great-wave',
    title: 'The Great Wave off Kanagawa',
    artist: 'Katsushika Hokusai',
    year: 'c. 1831',
    src: '/data/paintings/great-wave/thumb.webp',
    alt: 'Katsushika Hokusai, The Great Wave off Kanagawa',
    widthClass: 'wide',
  },
  {
    id: 'liberty-leading-the-people',
    worldId: 'liberty-leading-the-people',
    title: 'Liberty Leading the People',
    artist: 'Eugène Delacroix',
    year: '1830',
    src: '/data/paintings/liberty-leading-the-people/thumb.webp',
    alt: 'Eugène Delacroix, Liberty Leading the People',
    widthClass: 'wide',
  },
  {
    id: 'wanderer-above-the-sea-of-fog',
    worldId: 'wanderer-above-the-sea-of-fog',
    title: 'Wanderer above the Sea of Fog',
    artist: 'Caspar David Friedrich',
    year: 'c. 1818',
    src: '/data/paintings/wanderer-above-the-sea-of-fog/thumb.webp',
    alt: 'Caspar David Friedrich, Wanderer above the Sea of Fog',
    widthClass: 'medium',
  },
  {
    id: 'calling-of-saint-matthew',
    worldId: 'calling-of-saint-matthew',
    title: 'The Calling of Saint Matthew',
    artist: 'Caravaggio',
    year: 'c. 1599–1600',
    src: '/data/paintings/calling-of-saint-matthew/thumb.webp',
    alt: 'Caravaggio, The Calling of Saint Matthew',
    widthClass: 'wide',
  },
  {
    id: 'milkmaid',
    worldId: 'milkmaid',
    title: 'The Milkmaid',
    artist: 'Johannes Vermeer',
    year: 'c. 1658–1661',
    src: '/data/paintings/milkmaid/thumb.webp',
    alt: 'Johannes Vermeer, The Milkmaid',
    widthClass: 'narrow',
  },
  {
    id: 'saturn-devouring',
    worldId: 'saturn-devouring',
    title: 'Saturn Devouring His Son',
    artist: 'Francisco Goya',
    year: 'c. 1820–1823',
    src: '/data/paintings/saturn-devouring/thumb.webp',
    alt: 'Francisco Goya, Saturn Devouring His Son',
    widthClass: 'narrow',
  },
  {
    id: 'anatomy-lesson',
    worldId: 'anatomy-lesson',
    title: 'The Anatomy Lesson of Dr. Nicolaes Tulp',
    artist: 'Rembrandt van Rijn',
    year: '1632',
    src: '/data/paintings/anatomy-lesson/thumb.webp',
    alt: 'Rembrandt van Rijn, The Anatomy Lesson of Dr. Nicolaes Tulp',
    widthClass: 'wide',
  },
  {
    id: 'sunday-on-la-grande-jatte',
    worldId: 'sunday-on-la-grande-jatte',
    title: 'A Sunday on La Grande Jatte',
    artist: 'Georges Seurat',
    year: '1884–1886',
    src: '/data/paintings/sunday-on-la-grande-jatte/thumb.webp',
    alt: 'Georges Seurat, A Sunday on La Grande Jatte',
    widthClass: 'wide',
  },
]

/** Explore mode for a gallery card (`null` if no shipped world yet). */
export function galleryWorldKind(work: GalleryWork): WorldKind | null {
  return work.worldId ? worldKindOf(work.worldId) : null
}

export function galleryWorksOfKind(kind: WorldKind): GalleryWork[] {
  return galleryWorks.filter((w) => galleryWorldKind(w) === kind)
}

export const exportFormats = ['.glb', '.usdz', '.fbx', 'Unreal', 'Unity', 'WebXR link'] as const
