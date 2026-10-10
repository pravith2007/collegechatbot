export interface KnowledgeItem {
  keywords: string[];
  response: string;
  category: string;
}

export const expandedKnowledgeBase: Record<string, KnowledgeItem> = {
  // Admissions
  admissions: {
    keywords: ['admission', 'சேர்க்கை', 'விண்ணப்பம்', 'cutoff', 'கட்ஆஃப்', 'TNEA', 'counselling', 'கவுன்சிலிங்'],
    response: `🎓 கொங்கு பொறியியல் கல்லூரி சேர்க்கை 2025-26 தகவல்கள்:

📋 UG Courses: B.E/B.Tech (14 branches)
📚 PG Courses: M.E/M.Tech, MCA, MBA
🏛️ TNEA counselling மூலம் admission
💰 Annual fees: ₹75,000 - ₹1,25,000 (approx)
📞 Admission helpline: 04257-226688
🌐 Online application: www.kongu.edu

🏆 NAAC A++ accredited
📈 NIRF Ranking: 101-150 band
⭐ Career360 AAAA Grade

மேலும் தகவல்களுக்கு college office-ல் தொடர்பு கொள்ளுங்கள்!`,
    category: 'admission'
  },

  // Campus Locations - Maps links
  maharaja_auditorium: {
    keywords: ['maharaja auditorium', 'auditorium', 'மகாராஜா அரங்கம்', 'அரங்கம்', 'hall location'],
    response: `📍 Maharaja Auditorium (KEC)

🗺️ Google Maps: https://maps.app.goo.gl/BX8SNrCiNfeeATtB8`,
    category: 'location'
  },

  power_house: {
    keywords: ['kongu power house', 'power house', 'பவர் ஹவுஸ்', 'electric room'],
    response: `📍 Kongu Power House

🗺️ Google Maps: https://maps.app.goo.gl/oakwNPCqdwkvHJqG7`,
    category: 'location'
  },

  ece_block: {
    keywords: ['ece block', 'ece', 'electronics and communication block', 'இஇஇ துறை', 'ece building'],
    response: `📍 ECE Block (Electronics & Communication)

🗺️ Google Maps: https://maps.app.goo.gl/r7EeUo2pAkGZtx3i9`,
    category: 'location'
  },

  central_library_map: {
    keywords: ['central library map', 'central library location', 'library location', 'நூலகம் எங்கே', 'central library'],
    response: `📍 Central Library (KEC)

🗺️ Google Maps: https://maps.app.goo.gl/dBQQvTHvS3SLtKNE6`,
    category: 'location'
  },

  food_court: {
    keywords: ['food court', 'canteen', 'mess court', 'உணவகம்', 'கேன்டீன்'],
    response: `📍 Food Court @ KEC

🗺️ Google Maps: https://maps.app.goo.gl/FxHfL1uNUYBtVx9`,
    category: 'location'
  },

  playground: {
    keywords: ['playground', 'ground', 'sports ground', 'விளையாட்டு மைதானம்', 'கிரௌண்ட்'],
    response: `📍 Kongu Engineering College Playground

🗺️ Google Maps: https://maps.app.goo.gl/hgUdrVMxkkzHdxWW7`,
    category: 'location'
  },

  // Departments - Expanded with detailed info
  departments: {
    keywords: ['department', 'துறை', 'branches', 'course', 'கோர்ஸ்', 'engineering', 'பொறியியல்'],
    response: `🏛️ கொங்கு பொறியியல் கல்லூரியில் உள்ள துறைகள் (2025-26):

🚗 Automobile Engineering - 30 seats (Dr. P.C. முருகன்)
🏗️ Civil Engineering - 60 seats (Dr. S. பாலாஜி) + M.E Structural (12)
🔧 Mechanical Engineering - 60 seats (Dr. P. செல்வகுமார்)
🤖 Mechatronics Engineering - 120 seats (Dr. B. மீனாட்சி பிரியா)
📡 Electronics & Instrumentation - 120 seats (Dr. S.J. சூஜி பிரசாத்)
⚡ Electrical & Electronics - 120 seats (Dr. M. கார்த்திக்)
📻 Electronics & Communication - 240 seats (Dr. N. கஸ்துரி) + M.E VLSI (6)
💻 Computer Science Engineering - 360 seats (Dr. S. மல்லிகா) + M.E CSE (12)
🌐 Information Technology - 180 seats (Dr. S. ஆனந்தமுருகன்)
🧠 AI & Data Science - புதிய துறை
🎨 Computer Science & Design - புதிய துறை
🧪 Chemical Engineering
🍃 Food Technology

மொத்தம் 14+ UG departments உள்ளன!`,
    category: 'academic'
  },

  // Library - Enhanced
  library: {
    keywords: ['library', 'நூலகம்', 'books', 'புத்தகம்', 'timing', 'நேரம்', 'digital'],
    response: `📚 கொங்கு பொறியியல் கல்லூரி நூலக தகவல்கள்:

🏢 Central Library - 3 மாடிகள், விசாலமான வாசிப்பு அறைகள்
🕐 திங்கள் - வெள்ளி: காலை 8:00 - இரவு 8:00
🕐 சனி: காலை 8:00 - மாலை 5:00
📖 2+ லட்சம் books மற்றும் journals
💻 Digital library with e-resources
🔍 Online catalog system (OPAC)
📱 Mobile app available - "KEC Library"
🌐 IEEE, ACM, Springer digital access
📺 Audio-visual section
🔒 24/7 reading hall (விரைவில்!)
📋 Inter-library loan facility

நூலக card-க்கு student ID கொண்டு வாருங்கள்!`,
    category: 'facilities'
  },

  // Hostel - Enhanced
  hostel: {
    keywords: ['hostel', 'விடுதி', 'accommodation', 'தங்குமிடம்', 'mess', 'உணவு'],
    response: `🏠 கொங்கு பொறியியல் கல்லூரி விடுதி வசதிகள்:

👥 Boys மற்றும் Girls separate hostels
🏢 3000+ students capacity
🍽️ Multi-cuisine mess facility (South Indian, North Indian)
🏃‍♂️ Sports & recreation facilities
🔒 24/7 security with CCTV
💧 Pure RO water supply
🔌 Wi-Fi மற்றும் power backup
🚌 College bus service
🧺 Laundry facilities
🏥 Medical room with first aid
📚 Study rooms மற்றும் common areas

💰 Annual hostel fees: ₹45,000 - ₹65,000
🍽️ Mess fees: ₹25,000 - ₹30,000 per year

Hostel admission-க்கு separate application தேவை!`,
    category: 'facilities'
  },

  // Placement - Enhanced with latest data
  placement: {
    keywords: ['placement', 'வேலைவாய்ப்பு', 'job', 'company', 'campus', 'salary', 'package'],
    response: `💼 கொங்கு பொறியியல் கல்லூரி Placement தகவல்கள் (2025 batch):

📈 Placement percentage: 85%+ consistently
💼 120+ companies visit annually
💰 Highest package: ₹45+ LPA (International offers)
📊 Average package: ₹4.5 LPA
🎯 8 LPA+ offers: 200+ students

🏢 Top recruiters:
• TCS, Infosys, Wipro, Cognizant
• Zoho, PayPal, Amazon
• Microsoft, Google (selected students)
• L&T, Ashok Leyland, TVS
• HDFC Bank, ICICI Bank

📞 Placement cell: 04257-226655
📧 Email: placement@kongu.edu
🎓 Pre-placement training programs
💡 Soft skills மற்றும் technical training

Placement cell-ல் resume preparation help கிடைக்கும்!`,
    category: 'placement'
  },

  // Contact - Enhanced
  contact: {
    keywords: ['contact', 'phone', 'email', 'address', 'தொடர்பு', 'முகவரி', 'location'],
    response: `📍 கொங்கு பொறியியல் கல்லூரி தொடர்பு விவரங்கள்:

🏛️ முகவரி: Perundurai, Erode - 638060, Tamil Nadu
📞 Main office: 04257-226600
📞 Admission: 04257-226688
📞 Placement: 04257-226655
📧 Email: info@kongu.edu
🌐 Website: www.kongu.edu
📱 Mobile app: "KEC Connect"

🚌 Bus routes: Erode, Coimbatore, Salem, Tirupur
🚂 Nearest railway: Erode Junction (15 km)
✈️ Nearest airport: Coimbatore (60 km)

🕐 Office நேரம்: காலை 9:00 - மாலை 5:30 (திங்கள் - வெள்ளி)
🕐 சனி: காலை 9:00 - மதியம் 1:00

Emergency contact: 04257-226600 (24/7)`,
    category: 'contact'
  },

  // Fees - Enhanced
  fees: {
    keywords: ['fees', 'கட்டணம்', 'cost', 'செலவு', 'payment', 'scholarship', 'financial'],
    response: `💰 கொங்கு பொறியியல் கல்லூரி கட்டண விவரங்கள் (2025-26):

🎓 B.E/B.Tech annual fees:
• Management quota: ₹1,25,000
• Government quota: ₹75,000
• NRI quota: ₹2,50,000

📚 M.E/M.Tech fees: ₹85,000 - ₹1,35,000
🏠 Hostel fees: ₹45,000 - ₹65,000
🍽️ Mess fees: ₹25,000 - ₹30,000
🚌 Transport fees: ₹15,000 - ₹25,000

💳 Payment modes:
• Online payment portal
• Demand Draft
• Cash (office counter)

🎓 Scholarships available:
• Merit scholarships
• Government scholarships
• Minority scholarships
• Sports scholarships

Fee structure மாறலாம் - latest info-க்கு office-ல் confirm செய்யுங்கள்!`,
    category: 'fees'
  },

  // Rankings - New section
  rankings: {
    keywords: ['ranking', 'தரவரிசை', 'NIRF', 'NAAC', 'accreditation', 'grade'],
    response: `🏆 கொங்கு பொறியியல் கல்லூரி தரவரிசை மற்றும் அங்கீகாரங்கள்:

🥇 NIRF 2024: 101-150 band (Engineering category)
⭐ NAAC: A++ Grade (Highest accreditation)
📊 Career360 2024: AAAA Grade
🎯 Business Today: 123rd rank (Best B-Schools)
🏛️ HANSA Research: 58th rank (including IITs, NITs)

🌟 சிறப்பு அம்சங்கள்:
• 41 ஆண்டுகள் சிறந்து விளங்குதல்
• Anna University affiliated
• AICTE approved
• NBA accredited programs
• ISO 9001:2015 certified

🤝 100+ MoUs with top companies
🌍 International collaborations
🔬 Research excellence
💡 Innovation ecosystem

தமிழ்நாட்டின் top 10 engineering colleges-ல் ஒன்று!`,
    category: 'achievements'
  },

  // Facilities - New comprehensive section
  facilities: {
    keywords: ['facilities', 'வசதிகள்', 'infrastructure', 'lab', 'sports', 'canteen'],
    response: `🏛️ கொங்கு பொறியியல் கல்லூரி வசதிகள்:

🔬 Academic facilities:
• 50+ well-equipped laboratories
• Smart classrooms with projectors
• High-speed Wi-Fi campus
• Digital library resources

🏃‍♂️ Sports facilities:
• Cricket ground, Football field
• Basketball, Volleyball courts
• Indoor games complex
• Gymnasium with modern equipment

🍽️ Food & Dining:
• Multiple canteens
• Food court with variety
• Hygienic mess facilities
• 24/7 tea/coffee stalls

🚌 Transport:
• College buses from major cities
• Safe transportation for girls
• Parking facilities

🏥 Health & Safety:
• Medical center with qualified doctor
• Ambulance facility
• 24/7 security
• CCTV surveillance

🎭 Cultural facilities:
• Auditorium (1000+ capacity)
• Seminar halls
• Music & dance rooms
• Photography studio`,
    category: 'facilities'
  },

  // Events - New section
  events: {
    keywords: ['events', 'நிகழ்வுகள்', 'cultural', 'technical', 'fest', 'competition'],
    response: `🎉 கொங்கு பொறியியல் கல்லூரி நிகழ்வுகள்:

🎭 Annual Events:
• Annual Day celebration
• Graduation Day ceremony
• Freshers Day welcome
• Farewell for final years

💻 Technical Events:
• E-Horizon (Technical fest)
• Hackathons மற்றும் coding competitions
• Project exhibitions
• Industry expert lectures

🎨 Cultural Events:
• Inter-department competitions
• Music மற்றும் dance programs
• Drama மற்றும் literary events
• Photography contests

🏆 Sports Events:
• Inter-college tournaments
• Annual sports meet
• Indoor games competitions
• Fitness challenges

🌟 Special Programs:
• Industry visits
• Internship programs
• Placement drives
• Alumni meets

📅 Academic calendar-ல் எல்லா events-ம் mention பண்ணப்பட்டிருக்கும்!`,
    category: 'events'
  }
};

// Enhanced response matching with better accuracy
export const findBestResponse = (userMessage: string): string => {
  const lowerMessage = userMessage.toLowerCase();
  
  // Greeting responses
  const greetings = ['வணக்கம்', 'hello', 'hi', 'hey', 'good morning', 'good evening'];
  if (greetings.some(greeting => lowerMessage.includes(greeting))) {
    return "வணக்கம்! நான் KEC AI Assistant. கொங்கு பொறியியல் கல்லூரி பற்றி என்ன தெரிந்து கொள்ள வேண்டும்? admission, fees, departments, library, hostel, placement, rankings, facilities, events போன்ற topics பற்றி கேட்கலாம் 😊";
  }

  // Thank you responses
  const thanks = ['நன்றி', 'thank', 'thanks', 'தேங்க்யூ'];
  if (thanks.some(thank => lowerMessage.includes(thank))) {
    return "மகிழ்ச்சி! வேறு ஏதாவது doubt இருந்தா கேளுங்க. KEC-ல study பண்ணுவது exciting experience ஆ இருக்கும்! 🎓 எப்போதும் உதவுவதற்கு நான் இங்கே இருக்கிறேன்.";
  }

  // Find best matching response based on keywords
  let bestMatch = '';
  let maxMatches = 0;

  for (const data of Object.values(expandedKnowledgeBase)) {
    const matches = data.keywords.filter(keyword => 
      lowerMessage.includes(keyword.toLowerCase())
    ).length;

    if (matches > maxMatches) {
      maxMatches = matches;
      bestMatch = data.response;
    }
  }

  if (bestMatch) {
    return bestMatch;
  }

  // Enhanced default response with helpful suggestions
  return `மன்னிக்கவும், அந்த தகவல் தற்போது என்னிடம் இல்லை. 

🔍 இந்த topics பற்றி கேட்கலாம்:
• admission, fees, scholarship
• departments, courses, branches  
• library, hostel, mess
• placement, companies, salary
• rankings, NAAC, NIRF
• facilities, labs, sports
• events, cultural, technical

📞 Direct contact: 04257-226600
🌐 Website: www.kongu.edu

வேறு எதாவது specific-ஆ கேட்க வேண்டுமா? 😊`;
};
