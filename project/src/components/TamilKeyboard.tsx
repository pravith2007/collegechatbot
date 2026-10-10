import React, { useState } from 'react';
import { X, Backpack as Backspace, Space, Globe } from 'lucide-react';

interface TamilKeyboardProps {
  onKeyPress: (key: string) => void;
  onClose: () => void;
  isVisible: boolean;
}

const TamilKeyboard: React.FC<TamilKeyboardProps> = ({ onKeyPress, onClose, isVisible }) => {
  const [currentLayout, setCurrentLayout] = useState<'tamil' | 'english'>('tamil');
  const [isShiftPressed, setIsShiftPressed] = useState(false);

  if (!isVisible) return null;

  // Tamil keyboard layout similar to Google's Tamil keyboard
  const tamilLayout = [
    // Row 1 - Numbers and symbols
    ['௧', '௨', '௩', '௪', '௫', '௬', '௭', '௮', '௯', '௦'],
    // Row 2 - First row of consonants
    ['ஔ', 'ஐ', 'ஆ', 'ஈ', 'ஊ', 'ப', 'ர', 'க', 'த', 'ச', 'ட'],
    // Row 3 - Second row 
    ['ஓ', 'ஏ', 'அ', 'இ', 'உ', 'ய', 'ல', 'ன', 'வ', 'ெ', 'ே'],
    // Row 4 - Third row
    ['ஒ', 'எ', '்', 'ி', 'ு', 'ம', 'ந', 'ஜ', 'ள', 'ஞ'],
    // Row 5 - Fourth row with special characters
    ['ங', 'ழ', 'ற', 'ஸ', 'ஷ', 'ஹ', 'க்ஷ', 'ஶ்ரீ']
  ];

  // English QWERTY layout for phonetic typing
  const englishLayout = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
    ['z', 'x', 'c', 'v', 'b', 'n', 'm']
  ];

  // Common Tamil word suggestions
  const commonWords = [
    'கல்லூரி', 'சேர்க்கை', 'கட்டணம்', 'துறை', 'நூலகம்', 'விடுதி', 
    'வேலைவாய்ப்பு', 'தகவல்', 'விண்ணப்பம்', 'பொறியியல்', 'மாணவர்', 'ஆசிரியர்'
  ];

  // Phonetic mapping for English to Tamil
  const phoneticMap: { [key: string]: string } = {
    'a': 'அ', 'aa': 'ஆ', 'i': 'இ', 'ii': 'ஈ', 'u': 'உ', 'uu': 'ஊ',
    'e': 'எ', 'ee': 'ஏ', 'ai': 'ஐ', 'o': 'ஒ', 'oo': 'ஓ', 'au': 'ஔ',
    'ka': 'க', 'nga': 'ங', 'cha': 'ச', 'ja': 'ஜ', 'nya': 'ஞ',
    'ta': 'ட', 'na': 'ண', 'tha': 'த', 'nha': 'ந', 'pa': 'ப', 'ma': 'ம',
    'ya': 'ய', 'ra': 'ர', 'la': 'ல', 'va': 'வ', 'zha': 'ழ', 'lla': 'ள',
    'rra': 'ற', 'nna': 'ன', 'sa': 'ஸ', 'sha': 'ஷ', 'ha': 'ஹ'
  };

  const currentKeys = currentLayout === 'tamil' ? tamilLayout : englishLayout;

  const handleKeyPress = (key: string) => {
    if (currentLayout === 'english') {
      const tamilChar = phoneticMap[key.toLowerCase()];
      onKeyPress(tamilChar || key);
    } else {
      onKeyPress(key);
    }
  };

  const handleSpecialKey = (action: string) => {
    switch (action) {
      case 'backspace':
        onKeyPress('⌫');
        break;
      case 'space':
        onKeyPress(' ');
        break;
      case 'enter':
        onKeyPress('\n');
        break;
      case 'shift':
        setIsShiftPressed(!isShiftPressed);
        break;
    }
  };

  const handleWordSuggestion = (word: string) => {
    onKeyPress(word + ' ');
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-end justify-center z-50 p-0 sm:p-2">
      <div className="bg-white rounded-t-3xl sm:rounded-3xl w-full max-w-4xl shadow-2xl animate-slide-up flex flex-col max-h-[85vh] overflow-hidden border border-gray-200">
        
        {/* Keyboard Header */}
        <div className="flex justify-between items-center px-4 py-3 border-b border-gray-100 bg-gray-50/80">
          <div className="flex items-center space-x-3">
            <h3 className="text-sm sm:text-base font-bold text-gray-800">
              {currentLayout === 'tamil' ? 'தமிழ் விசைப்பலகை' : 'Tamil Keyboard (Phonetic)'}
            </h3>
            <button
              onClick={() => setCurrentLayout(currentLayout === 'tamil' ? 'english' : 'tamil')}
              className="flex items-center space-x-1.5 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold hover:bg-blue-200 transition"
            >
              <Globe className="w-3.5 h-3.5" />
              <span>{currentLayout === 'tamil' ? 'English' : 'தமிழ்'}</span>
            </button>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-200 text-gray-500 rounded-full transition"
            aria-label="Close Keyboard"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Word Suggestions (Horizontally Scrollable) */}
        <div className="px-3 py-2 border-b border-gray-100 overflow-x-auto no-scrollbar flex items-center space-x-1.5 bg-white">
          <span className="text-[10px] text-gray-400 font-medium uppercase tracking-wider shrink-0 mr-1">சொற்கள்:</span>
          {commonWords.map((word, index) => (
            <button
              key={index}
              onClick={() => handleWordSuggestion(word)}
              className="px-2.5 py-1 bg-gray-100 active:bg-blue-100 text-gray-700 active:text-blue-700 rounded-full text-xs whitespace-nowrap transition shrink-0 border border-gray-200"
            >
              {word}
            </button>
          ))}
        </div>

        {/* Main Keyboard Grid */}
        <div className="p-2 sm:p-4 overflow-y-auto bg-slate-50 flex-1">
          <div className="space-y-1.5 sm:space-y-2 max-w-2xl mx-auto">
            {currentKeys.map((row, rowIndex) => (
              <div key={rowIndex} className="flex justify-center gap-1 sm:gap-1.5 w-full">
                {row.map((key, keyIndex) => (
                  <button
                    key={keyIndex}
                    onClick={() => handleKeyPress(key)}
                    className={`
                      flex-1 min-w-[26px] max-w-[48px] h-10 sm:h-12 bg-white active:bg-blue-50
                      border border-gray-300 rounded-lg shadow-xs
                      text-xs sm:text-base font-medium text-gray-800 active:text-blue-600
                      transition duration-100 active:scale-95
                      flex items-center justify-center select-none touch-manipulation
                      ${currentLayout === 'english' ? 'uppercase' : ''}
                    `}
                  >
                    {isShiftPressed && currentLayout === 'english' ? key.toUpperCase() : key}
                  </button>
                ))}
              </div>
            ))}

            {/* Special Keys Bottom Row */}
            <div className="flex justify-center gap-1.5 sm:gap-2 mt-2 pt-1 border-t border-gray-200">
              {currentLayout === 'english' && (
                <button
                  onClick={() => handleSpecialKey('shift')}
                  className={`
                    px-3 sm:px-4 h-10 sm:h-12 rounded-lg text-xs sm:text-sm font-semibold transition active:scale-95 shadow-xs
                    ${isShiftPressed 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-200 active:bg-gray-300 text-gray-700'
                    }
                  `}
                >
                  ⇧ Shift
                </button>
              )}

              {/* Space Bar */}
              <button
                onClick={() => handleSpecialKey('space')}
                className="flex-1 max-w-xs h-10 sm:h-12 bg-gray-200 active:bg-gray-300 rounded-lg text-xs sm:text-sm font-medium text-gray-700 transition active:scale-95 shadow-xs flex items-center justify-center select-none"
              >
                <Space className="w-4 h-4 mr-1.5" />
                <span>Space</span>
              </button>

              {/* Backspace */}
              <button
                onClick={() => handleSpecialKey('backspace')}
                className="px-3 sm:px-4 h-10 sm:h-12 bg-rose-100 active:bg-rose-200 text-rose-700 rounded-lg text-xs sm:text-sm font-bold transition active:scale-95 shadow-xs flex items-center justify-center"
              >
                <Backspace className="w-4 h-4 mr-1" />
                <span>⌫</span>
              </button>

              {/* Enter Key */}
              <button
                onClick={() => handleSpecialKey('enter')}
                className="px-3 sm:px-4 h-10 sm:h-12 bg-emerald-600 active:bg-emerald-700 text-white rounded-lg text-xs sm:text-sm font-bold transition active:scale-95 shadow-xs"
              >
                ↵ Send
              </button>
            </div>
          </div>
        </div>

        {/* Keyboard Drawer Footer */}
        <div className="px-4 py-2 bg-white border-t border-gray-100 flex justify-between items-center text-[11px] text-gray-400 safe-bottom">
          <span>தமிழ் இயல்பான தட்டச்சு / Phonetic</span>
          <button onClick={onClose} className="font-semibold text-blue-600 hover:underline">
            மூடு / Done
          </button>
        </div>

      </div>
    </div>
  );
};

export default TamilKeyboard;