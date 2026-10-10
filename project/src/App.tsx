import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Bot, User, School, Phone, Mail, Globe, Keyboard, Mic, CornerDownLeft, 
  RefreshCw, ShieldCheck, Trash2, CheckCircle2, AlertCircle, Sparkles
} from 'lucide-react';
import TamilKeyboard from './components/TamilKeyboard';
import AdminDashboard from './components/AdminDashboard';
import { findBestResponse } from './data/knowledgeBase';

interface SourceItem {
  url?: string;
  title?: string;
  snippet?: string;
}

interface Message {
  id: number;
  text: string;
  isBot: boolean;
  timestamp: Date;
  sources?: (string | SourceItem)[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "வணக்கம்! நான் KEC AI Assistant. கொங்கு பொறியியல் கல்லூரி பற்றிய தகவல்களுக்கு நான் உதவுகிறேன். admission, departments, library, hostel, placement, rankings, facilities என்று கேட்கலாம் 😊\n\nதமிழில் type செய்ய keyboard icon-ஐ click செய்யுங்கள்! 🎹",
      isBot: true,
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showKeyboard, setShowKeyboard] = useState(false);
  const [isAdminOpen, setIsAdminOpen] = useState(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [sttLang, setSttLang] = useState<'auto' | 'ta-IN' | 'en-IN' | 'en-US'>('auto');
  const [isListening, setIsListening] = useState(false);
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Health check on mount and periodic polling
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/health`, { method: 'GET' });
        if (res.ok) {
          setIsBackendHealthy(true);
        } else {
          setIsBackendHealthy(false);
        }
      } catch {
        setIsBackendHealthy(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleClearChat = () => {
    if (window.confirm("Chat உரையாடலை அழிக்க விரும்புகிறீர்களா? (Clear chat history?)")) {
      setMessages([
        {
          id: 1,
          text: "வணக்கம்! நான் KEC AI Assistant. நீங்கள் புதிதாக உங்கள் கேள்விகளைக் கேட்கலாம். 😊",
          isBot: true,
          timestamp: new Date()
        }
      ]);
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: Date.now(),
      text: inputText,
      isBot: false,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const currentQuery = inputText;
    setInputText('');
    setIsTyping(true);

    try {
      // First attempt to query the Flask RAG backend
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: currentQuery })
      });

      if (response.ok) {
        const data = await response.json();
        const botAnswer = data.answer || data.response;
        if (botAnswer) {
          const botResponse: Message = {
            id: Date.now() + 1,
            text: botAnswer,
            isBot: true,
            timestamp: new Date(),
            sources: Array.isArray(data.sources) ? data.sources : []
          };
          setMessages(prev => [...prev, botResponse]);
          setIsBackendHealthy(true);
          return;
        }
      }
      throw new Error(`Server response error: ${response.status}`);
    } catch (err) {
      console.warn("Backend chat unavailable, using local knowledge base:", err);
      setIsBackendHealthy(false);
      const fallbackAnswer = findBestResponse(currentQuery);
      const botResponse: Message = {
        id: Date.now() + 1,
        text: fallbackAnswer,
        isBot: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botResponse]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleTamilKeyPress = (key: string) => {
    if (key === '⌫') {
      setInputText(prev => prev.slice(0, -1));
    } else if (key === '\n') {
      handleSendMessage();
    } else {
      setInputText(prev => prev + key);
    }

    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const renderMessageText = (text: string) => {
    if (!text) return null;
    const safeText = typeof text === 'string' ? text : String(text);
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = safeText.split(urlRegex);
    return parts.map((part, index) => {
      if (urlRegex.test(part)) {
        return (
          <a
            key={index}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 underline break-all font-medium inline-flex items-center gap-1"
          >
            <span>{part}</span>
          </a>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  const getActiveRecognitionLang = (): string => {
    if (sttLang !== 'auto') return sttLang;
    const hasTamil = /[\u0B80-\u0BFF]/.test(inputText);
    return hasTamil ? 'ta-IN' : 'en-IN';
  };

  const handleVoiceInput = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceNotice('Speech recognition is not available in this browser. Please use the on-screen Tamil keyboard.');
      setTimeout(() => setVoiceNotice(null), 5000);
      return;
    }

    if (!recognitionRef.current) {
      const recognition = new SpeechRecognition();
      recognition.lang = getActiveRecognitionLang();
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.maxAlternatives = 3;

      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }
        setInputText(prev => {
          const base = prev.trim().length > 0 ? prev + ' ' : '';
          return base + (finalTranscript || interimTranscript);
        });
      };

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);

      recognitionRef.current = recognition;
    }

    if (recognitionRef.current) {
      try { recognitionRef.current.lang = getActiveRecognitionLang(); } catch { }
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
      } catch (_) { }
    }
  };

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch { }
      }
    };
  }, []);

  const quickTopics = [
    { text: 'admission', emoji: '🎓' },
    { text: 'departments', emoji: '🏛️' },
    { text: 'library', emoji: '📚' },
    { text: 'hostel', emoji: '🏠' },
    { text: 'placement', emoji: '💼' },
    { text: 'fees', emoji: '💰' },
    { text: 'rankings', emoji: '🏆' },
    { text: 'facilities', emoji: '🏢' }
  ];

  return (
    <div className="flex flex-col min-h-screen h-[100dvh] bg-slate-100 text-gray-900 select-text overflow-hidden">
      {/* Top Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm shrink-0 z-30 pt-[env(safe-area-inset-top,0px)]">
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-blue-600 p-2 rounded-xl shadow-sm text-white">
              <School className="w-6 h-6 sm:w-7 sm:h-7" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-gray-900">KEC AI Assistant</h1>
                {/* RAG Connection Status Badge */}
                <div 
                  className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
                    isBackendHealthy 
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-300' 
                      : 'bg-amber-50 text-amber-700 border-amber-300'
                  }`}
                  title={isBackendHealthy ? "RAG Server Connected (Ollama/ChromaDB live)" : "Offline Mode (Using local knowledge base)"}
                >
                  {isBackendHealthy ? (
                    <>
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 animate-pulse" />
                      <span className="hidden sm:inline">RAG Online</span>
                      <span className="sm:hidden">Online</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-3 h-3 text-amber-600" />
                      <span className="hidden sm:inline">Offline Backup</span>
                      <span className="sm:hidden">Backup</span>
                    </>
                  )}
                </div>
              </div>
              <p className="text-gray-500 text-xs hidden sm:block">கொங்கு பொறியியல் கல்லூரி - NAAC A++ | NIRF Ranked</p>
            </div>
          </div>

          {/* Action Buttons: Admin Sync & Clear Chat */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* ADMIN SYNC BUTTON */}
            <button
              onClick={() => setIsAdminOpen(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white rounded-lg shadow-sm text-xs sm:text-sm font-semibold transition active:scale-95"
              title="Open Admin Knowledge Sync & Web Scraper Dashboard"
              id="admin-sync-btn"
            >
              <RefreshCw className="w-4 h-4 text-emerald-100" />
              <span>Admin Sync</span>
            </button>

            {/* Clear Chat Button */}
            <button
              onClick={handleClearChat}
              className="p-1.5 sm:px-2.5 sm:py-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition border border-transparent hover:border-red-200"
              title="Clear chat history"
            >
              <Trash2 className="w-4 h-4" />
              <span className="hidden md:inline ml-1 text-xs">Clear</span>
            </button>

            {/* Contact links on large screens */}
            <div className="hidden lg:flex items-center space-x-4 text-xs text-gray-500 pl-2 border-l border-gray-200">
              <a href="tel:04257226600" className="flex items-center space-x-1 hover:text-blue-600">
                <Phone className="w-3.5 h-3.5" />
                <span>04257-226600</span>
              </a>
              <a href="mailto:info@kongu.edu" className="flex items-center space-x-1 hover:text-blue-600">
                <Mail className="w-3.5 h-3.5" />
                <span>info@kongu.edu</span>
              </a>
              <a href="https://kongu.ac.in" target="_blank" rel="noreferrer" className="flex items-center space-x-1 hover:text-blue-600">
                <Globe className="w-3.5 h-3.5" />
                <span>kongu.ac.in</span>
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Main Chat Container */}
      <main className="flex-1 flex flex-col max-w-4xl w-full mx-auto p-2 sm:p-4 overflow-hidden min-h-0">
        <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col overflow-hidden min-h-0">
          
          {/* Sub Header Notice */}
          <div className="px-4 py-2 bg-slate-50 border-b border-gray-200 flex items-center justify-between text-xs text-gray-600 shrink-0">
            <div className="flex items-center space-x-2">
              <Bot className="w-4 h-4 text-blue-600" />
              <span className="font-medium">KEC Bilingual Assistant (Tamil & English)</span>
            </div>
            <div className="flex items-center space-x-1 text-slate-500">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span className="hidden sm:inline">Official KEC Grounded RAG</span>
            </div>
          </div>

          {/* Voice notice if unsupported */}
          {voiceNotice && (
            <div className="px-4 py-2 bg-amber-50 border-b border-amber-200 text-amber-800 text-xs flex items-center justify-between">
              <span>{voiceNotice}</span>
              <button onClick={() => setVoiceNotice(null)} className="text-amber-900 font-bold ml-2">✕</button>
            </div>
          )}

          {/* Message List */}
          <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3.5 bg-slate-50/60 min-h-0">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.isBot ? 'justify-start' : 'justify-end'}`}
              >
                <div className={`flex items-start space-x-2 max-w-[90%] sm:max-w-[80%] ${
                  message.isBot ? 'flex-row' : 'flex-row-reverse space-x-reverse'
                }`}>
                  <div className={`p-1.5 sm:p-2 rounded-full shrink-0 ${
                    message.isBot ? 'bg-blue-600 text-white' : 'bg-emerald-600 text-white'
                  }`}>
                    {message.isBot ? <Bot className="w-4 h-4 sm:w-5 sm:h-5" /> : <User className="w-4 h-4 sm:w-5 sm:h-5" />}
                  </div>
                  <div className={`p-3 sm:p-3.5 rounded-2xl shadow-sm ${
                    message.isBot
                      ? 'bg-white text-gray-800 border border-gray-200 rounded-tl-sm'
                      : 'bg-blue-600 text-white rounded-tr-sm'
                  }`}>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed break-words">
                      {renderMessageText(message.text)}
                    </div>

                    {/* Citations if available */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2.5 pt-2 border-t border-gray-100 text-[11px] text-gray-500">
                        <span className="font-semibold text-gray-600">Official Sources:</span>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {message.sources.map((src, i) => {
                            const url = typeof src === 'string' ? src : (src.url || 'https://kongu.ac.in/');
                            const label = typeof src === 'string' ? src : (src.title || src.url || 'KEC Official Source');
                            return (
                              <a
                                key={i}
                                href={url}
                                target="_blank"
                                rel="noreferrer"
                                className="px-2 py-0.5 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded text-[10px] truncate max-w-[220px] border border-blue-100 inline-block font-medium"
                                title={url}
                              >
                                {label}
                              </a>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    <div className={`text-[10px] mt-1.5 ${message.isBot ? 'text-gray-400' : 'text-blue-100 text-right'}`}>
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-2">
                  <div className="p-2 rounded-full bg-blue-600 text-white shrink-0">
                    <Bot className="w-4 h-4 sm:w-5 sm:h-5" />
                  </div>
                  <div className="p-3 bg-white border border-gray-200 rounded-2xl shadow-sm flex items-center space-x-1.5">
                    <span className="text-xs text-gray-500 font-medium">பதில் தயாராகிறது...</span>
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0.15s]"></div>
                    <div className="w-2 h-2 bg-blue-300 rounded-full animate-bounce [animation-delay:0.3s]"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Topics Pills */}
          <div className="px-3 py-2 bg-white border-t border-gray-100 overflow-x-auto whitespace-nowrap scrollbar-none flex items-center space-x-1.5 shrink-0">
            {quickTopics.map((topic) => (
              <button
                key={topic.text}
                onClick={() => setInputText(topic.text)}
                className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 rounded-full border border-slate-200 transition shrink-0 active:scale-95"
              >
                <span>{topic.emoji}</span>
                <span className="capitalize">{topic.text}</span>
              </button>
            ))}
          </div>

          {/* Fixed Input Bar */}
          <div className="p-2.5 sm:p-3 bg-white border-t border-gray-200 shrink-0 pb-[max(0.75rem,env(safe-area-inset-bottom,0px))]">
            <div className="flex items-center space-x-2">
              <div className="flex-1 relative flex items-center">
                <textarea
                  ref={textareaRef}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="உங்கள் கேள்வியை இங்கே டைப் செய்யுங்கள்..."
                  className="w-full pl-3 pr-10 py-2.5 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm bg-gray-50/50"
                  rows={1}
                  style={{ minHeight: '44px', maxHeight: '100px' }}
                />
                {/* Tamil Keyboard Toggle Button */}
                <button
                  type="button"
                  onClick={() => setShowKeyboard(!showKeyboard)}
                  className={`absolute right-2 p-1.5 rounded-lg transition ${
                    showKeyboard ? 'bg-blue-100 text-blue-700' : 'text-gray-400 hover:text-gray-600'
                  }`}
                  title="Tamil Keyboard (தமிழ் விசைப்பலகை)"
                >
                  <Keyboard className="w-5 h-5" />
                </button>
              </div>

              {/* Language Selector for Voice */}
              <select
                value={sttLang}
                onChange={(e) => setSttLang(e.target.value as any)}
                className="hidden sm:block px-2 py-2.5 bg-gray-100 text-gray-700 rounded-xl text-xs border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                title="Voice Input Language"
              >
                <option value="auto">Auto</option>
                <option value="ta-IN">தமிழ்</option>
                <option value="en-IN">English</option>
              </select>

              {/* Voice Mic Button */}
              <button
                type="button"
                onClick={handleVoiceInput}
                className={`p-2.5 rounded-xl border transition ${
                  isListening 
                    ? 'bg-red-500 text-white border-red-600 animate-pulse' 
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700 border-gray-300'
                }`}
                title={isListening ? "Stop listening" : "Voice input (Tamil/English)"}
              >
                <Mic className="w-5 h-5" />
              </button>

              {/* Send Button */}
              <button
                type="button"
                onClick={handleSendMessage}
                disabled={!inputText.trim() || isTyping}
                className="p-2.5 sm:px-4 sm:py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center font-medium active:scale-95 shrink-0"
                title="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Tamil Keyboard Drawer / Component */}
      <TamilKeyboard
        isVisible={showKeyboard}
        onKeyPress={handleTamilKeyPress}
        onClose={() => setShowKeyboard(false)}
      />

      {/* Admin Sync & Scraper Modal */}
      <AdminDashboard
        isOpen={isAdminOpen}
        onClose={() => setIsAdminOpen(false)}
        apiBaseUrl={API_BASE_URL}
      />
    </div>
  );
}

export default App;