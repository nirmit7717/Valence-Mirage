// ═══════════════════════════════════════════════
//  ThemeManager — Dynamic theming + ambience
// ═══════════════════════════════════════════════

export const THEMES = {
  fantasy:      { gradient: 'linear-gradient(135deg, #0d0221 0%, #150535 40%, #1a0a3e 70%, #0a0a1a 100%)', accent: '#c9a84c', animClass: 'amb-fantasy' },
  dark_fantasy: { gradient: 'linear-gradient(135deg, #0a0208 0%, #1a0515 40%, #0f0a1a 70%, #050208 100%)', accent: '#8b0000', animClass: 'amb-dark-fantasy' },
  horror:       { gradient: 'linear-gradient(135deg, #0a0000 0%, #1a0505 40%, #200a0a 70%, #0a0000 100%)', accent: '#cc2222', animClass: 'amb-horror' },
  sci_fi:       { gradient: 'linear-gradient(135deg, #000a14 0%, #001428 40%, #000f1f 70%, #000510 100%)', accent: '#00aaff', animClass: 'amb-scifi' },
  desert:       { gradient: 'linear-gradient(135deg, #1a1005 0%, #2a1a0a 40%, #1f150a 70%, #0a0805 100%)', accent: '#d4a24c', animClass: 'amb-desert' },
  forest:       { gradient: 'linear-gradient(135deg, #020a02 0%, #0a1a0a 40%, #051505 70%, #020802 100%)', accent: '#4a8c4a', animClass: 'amb-forest' },
  ocean:        { gradient: 'linear-gradient(135deg, #020a14 0%, #051520 40%, #0a1a2a 70%, #020510 100%)', accent: '#2277aa', animClass: 'amb-ocean' },
  underdark:    { gradient: 'linear-gradient(135deg, #050005 0%, #0a050f 40%, #080318 70%, #020005 100%)', accent: '#7744aa', animClass: 'amb-underdark' },
  mountain:     { gradient: 'linear-gradient(135deg, #0a0a0f 0%, #12121a 40%, #0f0f18 70%, #080810 100%)', accent: '#8899aa', animClass: 'amb-mountain' },
  ruins:        { gradient: 'linear-gradient(135deg, #0a0805 0%, #15120a 40%, #100e08 70%, #080605 100%)', accent: '#8a7a5a', animClass: 'amb-ruins' },
  default:      { gradient: 'linear-gradient(135deg, #0a0a0f 0%, #0f0f18 50%, #0a0a12 100%)', accent: '#c9a84c', animClass: '' },
};

const KEYWORD_MAP = [
  { keywords: ['undead', 'zombie', 'skeleton', 'necromanc', 'crypt', 'grave', 'haunt', 'ghost', 'wraith', 'vampire'], theme: 'horror' },
  { keywords: ['castle', 'dragon', 'king', 'queen', 'throne', 'knight', 'quest', 'prophecy'], theme: 'fantasy' },
  { keywords: ['dark', 'shadow', 'abyss', 'void', 'corrupt', 'demon', 'infernal', 'hell', 'damnation'], theme: 'dark_fantasy' },
  { keywords: ['sci-fi', 'cyberpunk', 'space', 'neon', 'tech', 'android', 'laser', 'starship'], theme: 'sci_fi' },
  { keywords: ['desert', 'sand', 'oasis', 'dune', 'arid', 'scorch', 'pyramid', 'pharaoh'], theme: 'desert' },
  { keywords: ['forest', 'elf', 'elven', 'woodland', 'grove', 'druid', 'tree', 'nature', 'jungle'], theme: 'forest' },
  { keywords: ['ocean', 'sea', 'pirate', 'ship', 'island', 'water', 'triton', 'siren', 'coral'], theme: 'ocean' },
  { keywords: ['underdark', 'drow', 'cave', 'underground', 'cavern', 'deep', 'mind flayer', 'illithid'], theme: 'underdark' },
  { keywords: ['mountain', 'peak', 'summit', 'dwarf', 'dwarven', 'forge', 'cliff'], theme: 'mountain' },
  { keywords: ['ruin', 'ancient', 'temple', 'lost city', 'forgotten', 'crumble', 'decrepit'], theme: 'ruins' },
];

export function detectTheme(text) {
  if (!text) return 'default';
  const lower = text.toLowerCase();
  for (const m of KEYWORD_MAP) {
    if (m.keywords.some(kw => lower.includes(kw))) return m.theme;
  }
  return 'default';
}

export function getThemeFromCampaign(campaign) {
  const sources = [
    campaign?.setting || '',
    campaign?.theme || '',
    campaign?.title || '',
    campaign?.premise || '',
    campaign?.keywords || '',
  ].join(' ');
  return detectTheme(sources);
}

// Ambience CSS — injected once
let ambienceInjected = false;

export function injectAmbienceCSS() {
  if (ambienceInjected) return;
  ambienceInjected = true;
  const style = document.createElement('style');
  style.id = 'ambienceStyles';
  style.textContent = `
    @keyframes ambPulse {
      0%, 100% { filter: brightness(1); }
      50% { filter: brightness(1.05); }
    }
    @keyframes ambGlow {
      0%, 100% { filter: brightness(1) saturate(1); }
      50% { filter: brightness(1.08) saturate(1.1); }
    }
    @keyframes ambRedPulse {
      0%, 100% { filter: brightness(1); }
      50% { filter: brightness(1.1) hue-rotate(-5deg); }
    }
    @keyframes ambNeon {
      0%, 100% { filter: brightness(1) hue-rotate(0deg); }
      33% { filter: brightness(1.06) hue-rotate(5deg); }
      66% { filter: brightness(1.03) hue-rotate(-3deg); }
    }
    .amb-fantasy .game-bg { animation: ambGlow 8s ease-in-out infinite; }
    .amb-dark-fantasy .game-bg { animation: ambPulse 6s ease-in-out infinite; }
    .amb-horror .game-bg { animation: ambRedPulse 4s ease-in-out infinite; }
    .amb-scifi .game-bg { animation: ambNeon 7s ease-in-out infinite; }
    .amb-desert .game-bg { animation: ambGlow 10s ease-in-out infinite; }
    .amb-forest .game-bg { animation: ambPulse 9s ease-in-out infinite; }
    .amb-ocean .game-bg { animation: ambGlow 11s ease-in-out infinite; }
    .amb-underdark .game-bg { animation: ambPulse 5s ease-in-out infinite; }
    .amb-mountain .game-bg { animation: ambPulse 12s ease-in-out infinite; }
    .amb-ruins .game-bg { animation: ambGlow 10s ease-in-out infinite; }
  `;
  document.head.appendChild(style);
}
