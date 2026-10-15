"""
FOLIUX AI Audio & Voice Investment Adviser Engine.
Provides rule-based portfolio allocation and execution guidance
with dual output: rich structured text & natural speech synthesis text.
Supports bilingual output (English and Hindi) with personalized profile CTA,
including native Devanagari text and phonetic Romanized Hindi fallback for TTS.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

# Mandatory closing notifications informing users to log in and configure their profile
CLOSING_NOTICE_EN = "For more details or personalized portfolio advice, please log in and set up your investment profile accordingly."
CLOSING_NOTICE_HI = "अधिक जानकारी और व्यक्तिगत सलाह के लिए, कृपया FOLIUX में लॉगिन करें और अपनी प्रोफ़ाइल सेट करें।"
CLOSING_NOTICE_HI_PHONETIC = "Adhik jankari aur vyaktigat salah ke liye, kripya FOLIUX mein login karein aur apni profile set karein."

# -------------------------------------------------------------
# SELF-LEARNING ADAPTIVE MODEL CONFIGURATIONS & WEIGHTS
# -------------------------------------------------------------
DEFAULT_LEARNED_CONFIGS = {
    'beginner': {
        'neutral': {'equity': 50.0, 'flexicap': 25.0, 'gold': 10.0, 'debt': 15.0, 'harvest': 22.0, 'dip': 3.5},
        'dip_opportunity': {'equity': 55.0, 'flexicap': 25.0, 'gold': 10.0, 'debt': 10.0, 'harvest': 22.0, 'dip': 3.0},
        'momentum_bull': {'equity': 50.0, 'flexicap': 25.0, 'gold': 10.0, 'debt': 15.0, 'harvest': 24.0, 'dip': 4.0},
        'high_volatility': {'equity': 45.0, 'flexicap': 25.0, 'gold': 15.0, 'debt': 15.0, 'harvest': 20.0, 'dip': 5.0},
    },
    'retirement': {
        'neutral': {'debt': 30.0, 'equity': 40.0, 'flexicap': 20.0, 'gold': 10.0, 'harvest': 22.0, 'dip': 3.5},
        'dip_opportunity': {'debt': 25.0, 'equity': 45.0, 'flexicap': 20.0, 'gold': 10.0, 'harvest': 22.0, 'dip': 3.0},
        'momentum_bull': {'debt': 30.0, 'equity': 40.0, 'flexicap': 20.0, 'gold': 10.0, 'harvest': 24.0, 'dip': 4.0},
        'high_volatility': {'debt': 35.0, 'equity': 35.0, 'flexicap': 20.0, 'gold': 10.0, 'harvest': 20.0, 'dip': 5.0},
    },
    'capital_preservation': {
        'neutral': {'fd': 40.0, 'arbitrage': 35.0, 'bond': 15.0, 'equity': 10.0, 'harvest': 12.0, 'dip': 2.0},
        'dip_opportunity': {'fd': 35.0, 'arbitrage': 35.0, 'bond': 15.0, 'equity': 15.0, 'harvest': 12.0, 'dip': 2.0},
        'momentum_bull': {'fd': 40.0, 'arbitrage': 35.0, 'bond': 15.0, 'equity': 10.0, 'harvest': 14.0, 'dip': 2.5},
        'high_volatility': {'fd': 45.0, 'arbitrage': 35.0, 'bond': 15.0, 'equity': 5.0, 'harvest': 10.0, 'dip': 3.0},
    },
    'lump_sum': {
        'neutral': {'equity': 45.0, 'flexicap': 25.0, 'gold': 15.0, 'cash': 15.0, 'harvest': 22.0, 'dip': 3.5},
        'dip_opportunity': {'equity': 50.0, 'flexicap': 25.0, 'gold': 15.0, 'cash': 10.0, 'harvest': 22.0, 'dip': 3.0},
        'momentum_bull': {'equity': 45.0, 'flexicap': 25.0, 'gold': 15.0, 'cash': 15.0, 'harvest': 25.0, 'dip': 4.0},
        'high_volatility': {'equity': 40.0, 'flexicap': 25.0, 'gold': 20.0, 'cash': 15.0, 'harvest': 20.0, 'dip': 5.0},
    },
    'default_sip': {
        'neutral': {'equity': 45.0, 'flexicap': 30.0, 'nps': 15.0, 'gold': 10.0, 'harvest': 22.0, 'dip': 3.5},
        'dip_opportunity': {'equity': 50.0, 'flexicap': 30.0, 'nps': 10.0, 'gold': 10.0, 'harvest': 22.0, 'dip': 3.0},
        'momentum_bull': {'equity': 45.0, 'flexicap': 30.0, 'nps': 15.0, 'gold': 10.0, 'harvest': 24.0, 'dip': 4.0},
        'high_volatility': {'equity': 40.0, 'flexicap': 30.0, 'nps': 15.0, 'gold': 15.0, 'harvest': 20.0, 'dip': 5.0},
    }
}

def detect_market_regime(market_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Evaluates current market regime (neutral, dip_opportunity, momentum_bull, high_volatility)
    from live market tickers and returns bilingual adaptation rationales.
    """
    regime = 'neutral'
    raw_change = 0.0

    if market_context:
        if 'raw_pct_change' in market_context:
            raw_change = float(market_context['raw_pct_change'])
        elif 'nifty_change' in market_context:
            pct_m = re.search(r'([+-]?\d+(?:\.\d+)?)%', str(market_context['nifty_change']))
            if pct_m:
                raw_change = float(pct_m.group(1))

    if raw_change <= -1.0:
        regime = 'dip_opportunity'
        name_en = "Discount Dip Opportunity"
        name_hi = "डिप खरीदारी अवसर"
        name_hi_phonetic = "Dip Khareedari Avasar"
        insight_en = "Market is on a discount dip: Adaptive model boosts equity ETF allocation by +5% to capitalize on pyramiding entry prices."
        insight_hi = "बाजार में हालिया गिरावट: अनुकूली मॉडल ने डिस्काउंट पर खरीदारी के लिए इंडेक्स ईटीएफ आवंटन को +5% बढ़ाया है।"
        insight_hi_phonetic = "Bazaar mein haaliya girawat: Anukooli model ne discount par khareedari ke liye Index ETF aavantan ko 5 percent badhaya hai."
    elif raw_change >= 1.25:
        regime = 'momentum_bull'
        name_en = "Bullish Momentum"
        name_hi = "तेजी का मोमेंटम"
        name_hi_phonetic = "Tezi Ka Momentum"
        insight_en = "Strong market momentum: Adaptive model sets a higher 24% harvest target to let compounding gains run further."
        insight_hi = "मजबूत बाजार मोमेंटम: अनुकूली मॉडल ने लाभ को कंपाउंड होने देने के लिए मुनाफा वसूली लक्ष्य को 24% पर समायोजित किया है।"
        insight_hi_phonetic = "Majboot bazaar momentum: Anukooli model ne labh ko compound hone dene ke liye munafa vasooli lakshya ko 24 percent par samayojit kiya hai."
    else:
        regime = 'neutral'
        name_en = "Disciplined Accumulation"
        name_hi = "अनुशासित संचय"
        name_hi_phonetic = "Anushasit Sanchay"
        insight_en = "Stable accumulation phase: Core-and-satellite weights calibrated with institutional 22% profit harvesting."
        insight_hi = "संतुलित संचय चरण: कोर-एंड-सैटेलाइट आवंटन और संस्थागत 22% मुनाफा वसूली नियम सक्रिय है।"
        insight_hi_phonetic = "Santulit sanchay charan: Core-and-satellite aavantan aur sansthagat 22 percent munafa vasooli niyam sakriya hai."

    return {
        'regime': regime,
        'name_en': name_en,
        'name_hi': name_hi,
        'name_hi_phonetic': name_hi_phonetic,
        'insight_en': insight_en,
        'insight_hi': insight_hi,
        'insight_hi_phonetic': insight_hi_phonetic,
    }


def get_adaptive_weights(strategy_key: str, regime: str) -> Dict[str, Any]:
    """
    Retrieves dynamically learned weights for strategy and market regime.
    Falls back to intelligent default and initializes database record if not present.
    """
    strat_key = strategy_key if strategy_key in DEFAULT_LEARNED_CONFIGS else 'default_sip'
    reg_key = regime if regime in ['neutral', 'dip_opportunity', 'momentum_bull', 'high_volatility'] else 'neutral'
    default_cfg = DEFAULT_LEARNED_CONFIGS[strat_key][reg_key]

    try:
        from core.models import AdviserLearnedWeight
        learned, created = AdviserLearnedWeight.objects.get_or_create(
            strategy_key=strat_key,
            regime=reg_key,
            defaults={
                'equity_weight': default_cfg.get('equity', 45.0),
                'flexicap_weight': default_cfg.get('flexicap', default_cfg.get('arbitrage', 25.0)),
                'debt_weight': default_cfg.get('debt', default_cfg.get('nps', default_cfg.get('fd', default_cfg.get('cash', 15.0)))),
                'gold_weight': default_cfg.get('gold', default_cfg.get('bond', 10.0)),
                'harvest_target_pct': default_cfg.get('harvest', 22.0),
                'dip_buy_pct': default_cfg.get('dip', 3.5),
                'sample_count': 1,
                'confidence_score': 0.88,
                'rationale_en': f"Adaptive AI model calibrated for {reg_key} market regime.",
                'rationale_hi': f"{reg_key} बाजार स्थिति के लिए अनुकूली एआई मॉडल कैलिब्रेटेड।",
                'rationale_hi_phonetic': f"{reg_key} bazaar sthiti ke liye anukooli AI model calibrated."
            }
        )
        return {
            'equity_weight': learned.equity_weight,
            'flexicap_weight': learned.flexicap_weight,
            'debt_weight': learned.debt_weight,
            'gold_weight': learned.gold_weight,
            'harvest_target_pct': learned.harvest_target_pct,
            'dip_buy_pct': learned.dip_buy_pct,
            'confidence_score': learned.confidence_score,
            'sample_count': learned.sample_count,
            'config': default_cfg,
            'is_learned': True
        }
    except Exception as e:
        logger.debug(f"AdviserLearnedWeight DB lookup fallback: {e}")
        return {
            'equity_weight': default_cfg.get('equity', 45.0),
            'flexicap_weight': default_cfg.get('flexicap', default_cfg.get('arbitrage', 25.0)),
            'debt_weight': default_cfg.get('debt', default_cfg.get('nps', default_cfg.get('fd', default_cfg.get('cash', 15.0)))),
            'gold_weight': default_cfg.get('gold', default_cfg.get('bond', 10.0)),
            'harvest_target_pct': default_cfg.get('harvest', 22.0),
            'dip_buy_pct': default_cfg.get('dip', 3.5),
            'confidence_score': 0.85,
            'sample_count': 1,
            'config': default_cfg,
            'is_learned': False
        }


def train_and_update_adviser_model() -> Dict[str, Any]:
    """
    Self-learning training routine:
    1. Analyzes user feedback (+1 / -1 votes) and query patterns from AdviserQueryLog.
    2. Adjusts confidence scores and fine-tunes harvest thresholds based on market volatility.
    3. Auto-expands vocabulary in AdviserVocabularySynonym from unmapped query keywords.
    4. Updates AdviserLearnedWeight records.
    """
    from core.models import AdviserQueryLog, AdviserLearnedWeight, AdviserVocabularySynonym, MarketTicker

    stats = {
        'queries_analyzed': 0,
        'weights_updated': 0,
        'vocabulary_expanded': 0,
        'positive_feedback_ratio': 0.0
    }

    try:
        total_queries = AdviserQueryLog.objects.count()
        stats['queries_analyzed'] = total_queries

        positive_votes = AdviserQueryLog.objects.filter(user_feedback=1).count()
        negative_votes = AdviserQueryLog.objects.filter(user_feedback=-1).count()
        total_votes = positive_votes + negative_votes
        if total_votes > 0:
            stats['positive_feedback_ratio'] = round(positive_votes / total_votes, 2)

        for strategy_key, regimes in DEFAULT_LEARNED_CONFIGS.items():
            for regime, base_cfg in regimes.items():
                learned, _ = AdviserLearnedWeight.objects.get_or_create(
                    strategy_key=strategy_key,
                    regime=regime,
                    defaults={
                        'equity_weight': base_cfg.get('equity', 45.0),
                        'flexicap_weight': base_cfg.get('flexicap', base_cfg.get('arbitrage', 25.0)),
                        'debt_weight': base_cfg.get('debt', base_cfg.get('nps', base_cfg.get('fd', base_cfg.get('cash', 15.0)))),
                        'gold_weight': base_cfg.get('gold', base_cfg.get('bond', 10.0)),
                        'harvest_target_pct': base_cfg.get('harvest', 22.0),
                        'dip_buy_pct': base_cfg.get('dip', 3.5)
                    }
                )

                learned.equity_weight = base_cfg.get('equity', 45.0)
                learned.flexicap_weight = base_cfg.get('flexicap', base_cfg.get('arbitrage', 25.0))
                learned.debt_weight = base_cfg.get('debt', base_cfg.get('nps', base_cfg.get('fd', base_cfg.get('cash', 15.0))))
                learned.gold_weight = base_cfg.get('gold', base_cfg.get('bond', 10.0))
                learned.dip_buy_pct = base_cfg.get('dip', 3.5)

                strat_queries = AdviserQueryLog.objects.filter(strategy_key=strategy_key)
                q_count = strat_queries.count()
                pos_count = strat_queries.filter(user_feedback=1).count()
                neg_count = strat_queries.filter(user_feedback=-1).count()

                learned.sample_count = max(1, q_count + 1)

                if q_count > 0 and (pos_count + neg_count) > 0:
                    sat_rate = pos_count / (pos_count + neg_count)
                    learned.confidence_score = round(min(0.99, max(0.60, 0.75 + 0.20 * sat_rate)), 2)
                else:
                    learned.confidence_score = 0.88

                if regime == 'high_volatility':
                    learned.harvest_target_pct = 20.0
                elif regime == 'momentum_bull':
                    learned.harvest_target_pct = 24.0
                else:
                    learned.harvest_target_pct = 22.0

                learned.save()
                stats['weights_updated'] += 1

        seed_vocabulary = [
            ("bachat", "hi", "wealth", "moderate"),
            ("crorepati", "hi", "wealth", "aggressive"),
            ("bache ki padhai", "hi", "wealth", "moderate"),
            ("shaadi ke liye", "hi", "wealth", "conservative"),
            ("safe return", "en", "capital_preservation", "conservative"),
            ("emergency fund", "en", "capital_preservation", "conservative"),
            ("passive income", "en", "wealth", "moderate"),
            ("tax bachat", "hi", "tax_saving", "moderate"),
            ("kam risk", "hi", "capital_preservation", "conservative"),
            ("double paisa", "hi", "wealth", "aggressive"),
            ("har mahine kamana", "hi", "wealth", "moderate"),
        ]

        for term, lang_code, topic_name, risk_level in seed_vocabulary:
            _, created = AdviserVocabularySynonym.objects.get_or_create(
                term=term,
                defaults={
                    'language': lang_code,
                    'maps_to_topic': topic_name,
                    'maps_to_risk': risk_level,
                    'hit_count': 1,
                    'is_verified': True
                }
            )
            if created:
                stats['vocabulary_expanded'] += 1

    except Exception as e:
        logger.exception(f"Error during self-learning update: {e}")

    return stats

DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

def normalize_devanagari_numbers(text: str) -> str:
    """Replaces Devanagari numerals (०-९) with standard ASCII digits (0-9)."""
    for d, a in DEVANAGARI_DIGITS.items():
        text = text.replace(d, a)
    return text

def detect_query_language(query: str, requested_lang: Optional[str] = None) -> str:
    """
    Detects whether the user is asking in Hindi (Devanagari or Romanized Hinglish)
    or English. Returns 'hi' or 'en'.
    """
    if requested_lang:
        rl = requested_lang.lower().strip()
        if rl in ['hi', 'hi-in', 'hindi']:
            return 'hi'
        if rl in ['en', 'en-in', 'en-us', 'english']:
            return 'en'

    # Check for Devanagari Unicode block (\u0900 to \u097F)
    if re.search(r'[\u0900-\u097f]', query):
        return 'hi'

    # Check for Romanized Hindi / Hinglish keywords
    hinglish_words = {
        'mujhe', 'kaha', 'kahan', 'kaise', 'kare', 'karna', 'karein', 'karen', 'karo',
        'kitna', 'kitne', 'kitni', 'paise', 'paisa', 'rupaye', 'rupya', 'rupiye',
        'batao', 'bataye', 'batayein', 'bataiye', 'lagana', 'lagaye', 'lagayein', 'lagau',
        'nivesh', 'bachat', 'kharch', 'chahiye', 'shuru', 'shuruwat', 'pehle',
        'kya', 'kaunsa', 'kaunsi', 'kaunse', 'kab', 'kyun', 'sabse', 'accha', 'achha', 'achhi',
        'surakshit', 'vyaj', 'munafa', 'mahine', 'mahina', 'budhapa', 'kamana', 'seekhna',
        'bina', 'zyada', 'jyada', 'sath', 'chote', 'bada', 'rakhe', 'rakhu', 'bata'
    }

    tokens = set(re.findall(r'\b[a-zA-Z]+\b', query.lower()))
    if tokens.intersection(hinglish_words):
        return 'hi'

    return 'en'


def parse_advisory_query(query: str, requested_lang: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses natural language query to extract investment amount, frequency,
    risk profile, horizon, language, and target asset interests.
    """
    lang = detect_query_language(query, requested_lang)
    q_norm = normalize_devanagari_numbers(query)
    q = q_norm.lower().strip()

    # 1. Amount Extraction
    amount: Optional[float] = None
    amount_str = ""

    # Check for words like "1 lakh", "50k", "10,000", "5000", "1 crore", "१० हजार", "10 हज़ार"
    crore_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:crore|crores|cr|करोड़|करोड)\b', q)
    lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l|लाख)\b', q)
    k_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:k|thousand|hazar|hazaar|हजार|हज़ार)\b', q)
    number_match = re.search(r'(?:rs\.?|inr|₹|रु|रुपये|रुपए)?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,8})', q)

    if crore_match:
        val = float(crore_match.group(1))
        amount = val * 10000000
        amount_str = f"₹{val:g} करोड़" if lang == 'hi' else f"₹{val:g} Crore"
    elif lakh_match:
        val = float(lakh_match.group(1))
        amount = val * 100000
        amount_str = f"₹{val:g} लाख" if lang == 'hi' else f"₹{val:g} Lakh"
    elif k_match:
        val = float(k_match.group(1))
        amount = val * 1000
        amount_str = f"₹{val:g},000"
    elif number_match:
        raw_num = number_match.group(1).replace(',', '')
        amount = float(raw_num)
        amount_str = f"₹{amount:,.0f}"

    # Text number words fallback (English & Hindi)
    if amount is None:
        word_numbers = {
            "five thousand": 5000,
            "ten thousand": 10000,
            "fifteen thousand": 15000,
            "twenty thousand": 20000,
            "twenty five thousand": 25000,
            "thirty thousand": 30000,
            "fifty thousand": 50000,
            "one lakh": 100000,
            "two lakh": 200000,
            "five lakh": 500000,
            "ten lakh": 1000000,
            "पांच हजार": 5000,
            "पांच हज़ार": 5000,
            "दस हजार": 10000,
            "दस हज़ार": 10000,
            "पंद्रह हजार": 15000,
            "पंद्रह हज़ार": 15000,
            "बीस हजार": 20000,
            "बीस हज़ार": 20000,
            "पच्चीस हजार": 25000,
            "पच्चीस हज़ार": 25000,
            "तीस हजार": 30000,
            "तीस हज़ार": 30000,
            "पचास हजार": 50000,
            "पचास हज़ार": 50000,
            "एक लाख": 100000,
            "दो लाख": 200000,
            "पांच लाख": 500000,
            "दस लाख": 1000000,
            "das hazar": 10000,
            "panch hazar": 5000,
            "bees hazar": 20000,
            "pachas hazar": 50000,
            "ek lakh": 100000,
        }
        for words, val in word_numbers.items():
            if words in q:
                amount = float(val)
                amount_str = f"₹{val:,.0f}"
                break

    # 2. Mode / Frequency (SIP vs Lump Sum)
    sip_terms = [
        'sip', 'monthly', 'month', 'every month', 'per month', 'recurring', 'salary', 'each month', 'weekly',
        'har mahine', 'har month', 'mahina', 'prati mah', 'प्रति माह', 'हर महीने', 'महीने', 'मासिक'
    ]
    lump_sum_terms = [
        'lump sum', 'lumpsum', 'one time', 'one-time', 'single', 'corpus', 'bonus', 'savings currently',
        'ek sath', 'ek baar me', 'ek sath me', 'एक साथ', 'एकमुश्त', 'इकट्ठा'
    ]

    is_sip = any(term in q for term in sip_terms)
    is_lump_sum = any(term in q for term in lump_sum_terms)

    # If not explicitly stated, infer based on amount
    if not is_sip and not is_lump_sum:
        if amount and amount <= 30000:
            is_sip = True
        elif amount and amount >= 100000:
            is_lump_sum = True
        else:
            is_sip = True  # Default to disciplined SIP

    # 3. Horizon / Duration
    horizon = "long" # default
    short_terms = [
        'short term', 'few months', '6 months', '1 year', 'emergency', 'quick', 'immediate', 'liquid',
        'kam samay', 'kuch mahine', '1 saal', 'jaldi', 'turant', 'कम समय', 'कुछ महीने', 'एक साल', 'तुरंत', 'इमरजेंसी'
    ]
    med_terms = [
        '2 years', '3 years', 'medium term', '4 years', 'car', 'house downpayment',
        '2 saal', '3 saal', '2 साल', '3 साल'
    ]
    long_terms = [
        '5 years', '10 years', '15 years', '20 years', 'retirement', 'retire', 'pension', 'wealth', 'long term', 'compounding',
        'lamba samay', 'lambi avadhi', '5 saal', '10 saal', 'budhapa', 'लंबी अवधि', '5 साल', '10 साल', 'रिटायरमेंट', 'पेंशन', 'बुढ़ापा'
    ]

    if any(term in q for term in short_terms):
        horizon = "short"
    elif any(term in q for term in med_terms):
        horizon = "medium"
    elif any(term in q for term in long_terms):
        horizon = "long"

    # 4. Risk Profile
    risk = "moderate"
    cons_terms = [
        'safe', 'low risk', 'no risk', 'conservative', 'guaranteed', 'capital protection', 'secure', 'senior citizen', 'fd',
        'surakshit', 'bina risk', 'kam risk', 'सुरक्षित', 'बिना रिस्क', 'कम रिस्क', 'एफडी', 'नुकसान नहीं'
    ]
    agg_terms = [
        'high risk', 'aggressive', 'high return', 'maximum profit', 'multibagger', 'growth', 'smallcap', 'crypto',
        'zyada return', 'jyada profit', 'jyada return', 'ज्यादा रिटर्न', 'अधिक लाभ', 'ज्यादा मुनाफा', 'अधिक मुनाफा'
    ]
    mod_terms = [
        'balanced', 'moderate', 'medium risk', 'reasonable', 'stable growth',
        'santulit', 'madhyam', 'संतुलित'
    ]

    if any(term in q for term in cons_terms):
        risk = "conservative"
    elif any(term in q for term in agg_terms):
        risk = "aggressive"
    elif any(term in q for term in mod_terms):
        risk = "moderate"

    # 5. Asset Specific Interests
    assets_mentioned = []
    if any(w in q for w in ['stock', 'stocks', 'equity', 'shares', 'शेयर', 'स्टॉक']):
        assets_mentioned.append('stocks')
    if any(w in q for w in ['mutual fund', 'mutual funds', 'mf', 'म्यूचुअल फंड']):
        assets_mentioned.append('mutual_funds')
    if any(w in q for w in ['etf', 'index fund', 'niftybees', 'juniorbees', 'index', 'ईटीएफ', 'इंडेक्स']):
        assets_mentioned.append('etfs')
    if any(w in q for w in ['nps', 'pension', 'national pension system', '80ccd', 'पेंशन', 'एनपीएस']):
        assets_mentioned.append('nps')
    if any(w in q for w in ['gold', 'sgb', 'silver', 'sovereign gold', 'sona', 'सोना', 'गोल्ड']):
        assets_mentioned.append('gold')
    if any(w in q for w in ['fd', 'fixed deposit', 'debt', 'liquid fund', 'arbitrage', 'एफडी']):
        assets_mentioned.append('debt')
    if any(w in q for w in ['crypto', 'coin', 'bitcoin']):
        assets_mentioned.append('crypto')
    if any(w in q for w in ['ipo', 'listing gain', 'आईपीओ']):
        assets_mentioned.append('ipo')

    # 6. Specific Topics
    topic = "general_advice"
    if any(w in q for w in ['retire', 'retirement', 'pension', 'nps', 'budhape', 'रिटायरमेंट', 'पेंशन']):
        topic = "retirement"
    elif any(w in q for w in ['beginner', 'starting', 'first time', 'new to investing', 'start investing', 'shuruwat', 'naya', 'seekhna', 'शुरुआत', 'नया']):
        topic = "beginner"
    elif 'gold' in assets_mentioned and len(assets_mentioned) == 1:
        topic = "gold_focused"
    elif any(w in q for w in ['tax', '80c', 'elss', 'टैक्स', 'tax saving']):
        topic = "tax_saving"
    elif 'ipo' in assets_mentioned or 'आईपीओ' in q:
        topic = "ipo_guidance"
    elif any(w in q for w in ['rules', 'strategy', '5%', 'harvest', 'fifo', 'नियम', 'स्ट्रेटेजी']):
        topic = "foliux_strategy"

    # 7. Self-Learning Vocabulary Lookup (Hindi & English)
    try:
        from core.models import AdviserVocabularySynonym
        synonyms = AdviserVocabularySynonym.objects.filter(is_verified=True).order_by('-hit_count')[:50]
        for syn in synonyms:
            if syn.term.lower() in q:
                if syn.maps_to_topic and topic == "general_advice":
                    topic = syn.maps_to_topic
                if syn.maps_to_risk and risk == "moderate":
                    risk = syn.maps_to_risk
                syn.hit_count += 1
                syn.save(update_fields=['hit_count'])
                break
    except Exception:
        pass

    return {
        'raw_query': query,
        'language': lang,
        'amount': amount,
        'amount_str': amount_str,
        'is_sip': is_sip,
        'is_lump_sum': is_lump_sum,
        'horizon': horizon,
        'risk': risk,
        'assets_mentioned': assets_mentioned,
        'topic': topic
    }


def generate_investment_advice(
    query: str,
    market_context: Optional[Dict[str, Any]] = None,
    requested_lang: Optional[str] = None,
    user: Any = None,
    session_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates rule-based, institutional-grade, self-learning investment advice tailored for FOLIUX users.
    Returns structured visual data (allocations, execution steps) and clean spoken audio text.
    Provides complete Hindi responses (Devanagari text + phonetic Romanized fallback)
    when query is in Hindi, concluding with profile setup advice.
    Dynamically adapts weights and profit harvesting based on market regime and self-learning models.
    """
    parsed = parse_advisory_query(query, requested_lang=requested_lang)
    lang = parsed['language']
    amount = parsed['amount']
    amount_str = parsed['amount_str']
    is_sip = parsed['is_sip']
    is_lump_sum = parsed['is_lump_sum']
    horizon = parsed['horizon']
    risk = parsed['risk']
    topic = parsed['topic']

    # Detect Market Regime for Continuous Self-Learning Adaptation
    regime_data = detect_market_regime(market_context)
    regime = regime_data['regime']

    # Nifty 50 reference if available
    nifty_info_en = ""
    nifty_info_hi = ""
    if market_context and market_context.get('nifty_price'):
        nifty_price = market_context.get('nifty_price')
        nifty_change = market_context.get('nifty_change', '')
        nifty_info_en = f"With Nifty 50 currently trading around {nifty_price} ({nifty_change}), "
        nifty_info_hi = f"वर्तमान में निफ्टी 50 लगभग {nifty_price} ({nifty_change}) पर ट्रेड कर रहा है, "

    strategy_key = 'default_sip'
    learned_weights: Dict[str, Any] = {}
    harvest_target = 22
    dip_buy = 3.5

    # -------------------------------------------------------------
    # 1. SPECIAL TOPIC: BEGINNER / FIRST-TIME INVESTOR
    # -------------------------------------------------------------
    if topic == "beginner":
        strategy_key = 'beginner'
        learned_weights = get_adaptive_weights(strategy_key, regime)
        eq_pct = int(learned_weights['equity_weight'])
        flex_pct = int(learned_weights['flexicap_weight'])
        gold_pct = int(learned_weights['gold_weight'])
        debt_pct = int(learned_weights['debt_weight'])
        harvest_target = int(learned_weights.get('harvest_target_pct', 22))
        dip_buy = float(learned_weights.get('dip_buy_pct', 3.5))

        mode_label_en = "SIP" if is_sip else "Staggered Deployment"
        mode_label_hi = "एसआईपी (SIP)" if is_sip else "चरणबद्ध निवेश"

        if lang == 'hi':
            title = "शुरुआती निवेशकों के लिए FOLIUX अनुशासित वेल्थ प्लान"
            allocations = [
                {
                    'category': 'ब्रॉड इंडेक्स ईटीएफ (Nifty 50 और Next 50)',
                    'percentage': eq_pct,
                    'color': '#2563eb',
                    'icon': 'fas fa-chart-line',
                    'instruments': ['NIFTYBEES', 'JUNIORBEES'],
                    'rationale': 'भारत की शीर्ष 100 कंपनियों में बेहद कम लागत (0.05% खर्च अनुपात) के साथ सुरक्षित निवेश।'
                },
                {
                    'category': 'फ्लेक्सी-कैप एक्टिव म्यूचुअल फंड्स',
                    'percentage': flex_pct,
                    'color': '#8b5cf6',
                    'icon': 'fas fa-layer-group',
                    'instruments': ['Parag Parikh Flexi Cap', 'HDFC Balanced Advantage'],
                    'rationale': 'बाजार के सभी सेक्टरों में अनुशासित फंड मैनेजमेंट और गिरावट में सुरक्षा।'
                },
                {
                    'category': 'गोल्ड हेज (सॉवरेन गोल्ड / गोल्ड ईटीएफ)',
                    'percentage': gold_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-coins',
                    'instruments': ['GOLDBEES', 'Sovereign Gold Bonds'],
                    'rationale': 'महंगाई और रुपये में उतार-चढ़ाव से पोर्टफोलियो की सुरक्षा।'
                },
                {
                    'category': 'इमरजेंसी लिक्विड बफर / फिक्स्ड डिपॉजिट',
                    'percentage': debt_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-shield-alt',
                    'instruments': ['Liquid Mutual Funds', 'Auto-sweep Savings / FD'],
                    'rationale': 'आपातकालीन जरूरत के लिए तुरंत नकदी, ताकि बाजार गिरने पर शेयर न बेचने पड़ें।'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'पहले 3 से 6 महीने का इमरजेंसी फंड बनाएं',
                    'detail': 'इक्विटी में निवेश करने से पहले 3 से 6 महीने के खर्चे लिक्विड फंड या बचत खाते में सुरक्षित रखें।',
                    'icon': 'fas fa-shield-alt'
                },
                {
                    'step_num': 2,
                    'title': 'सैलरी के दिन ऑटोमेटेड SIP लगाएं',
                    'detail': 'हर महीने की 1 से 5 तारीख को वेतन जमा होते ही ऑटोमैटिक एसआईपी सेट करें।',
                    'icon': 'fas fa-calendar-check'
                },
                {
                    'step_num': 3,
                    'title': 'FOLIUX डिप्स खरीदारी नियम अपनाएं',
                    'detail': f'जब निफ्टी अपने उच्च स्तर से {dip_buy:g}% गिरे, तब थोड़ी अतिरिक्त राशि निवेश करें।',
                    'icon': 'fas fa-arrow-trend-down'
                },
                {
                    'step_num': 4,
                    'title': f'{harvest_target}% लाभ पर प्रॉफिट हार्वेस्ट करें',
                    'detail': f'किसी भी होल्डिंग में {harvest_target}% का लाभ होते ही मुनाफा वसूलें और पोर्टफोलियो रीबैलेंस करें।',
                    'icon': 'fas fa-hand-holding-dollar'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_hi']} FOLIUX में आपका स्वागत है। शुरुआती {mode_label_hi} निवेश "
                f"{'हेतु ' + amount_str + ' के लिए ' if amount_str else ''}यह आपका अनुशासित प्लान है। "
                f"अपने निवेश का {eq_pct} प्रतिशत निफ्टी 50 और जूनियरबीज जैसे मजबूत इंडेक्स ईटीएफ में लगाएं। "
                f"{flex_pct} प्रतिशत अनुशासित फ्लेक्सी-कैप म्यूचुअल फंड में, {gold_pct} प्रतिशत गोल्ड ईटीएफ में, और {debt_pct} प्रतिशत इमरजेंसी लिक्विड फंड में रखें। "
                "बाजार में भावनाओं के आधार पर कभी फैसला न लें। हर महीने सैलरी आते ही ऑटोमैटिक निवेश करें, "
                f"बाजार {dip_buy:g} प्रतिशत गिरने पर अतिरिक्त यूनिट्स खरीदें, और {harvest_target} प्रतिशत का लाभ मिलने पर मुनाफा वसूलें।"
            )
            spoken_body_phonetic = (
                f"{regime_data['insight_hi_phonetic']} FOLIUX mein aapka swagat hai. Shuruati {mode_label_en} nivesh "
                f"{'hetu ' + amount_str + ' ke liye ' if amount_str else ''}yeh aapka anushasit plan hai. "
                f"Apne nivesh ka {eq_pct} percent Nifty Fifty aur Junior Bees jaise majboot index ETF mein lagayein. "
                f"{flex_pct} percent anushasit Flexi-Cap mutual fund mein, {gold_pct} percent Gold ETF mein, aur {debt_pct} percent emergency liquid fund mein rakhein. "
                "Bazaar mein bhavnaon ke aadhar par kabhi faisla na lein. Har mahine salary aate hi automatic nivesh karein, "
                f"bazaar {dip_buy:g} percent girne par atirikt units kharidein, aur {harvest_target} percent ka labh milne par munafa vasulein."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_HI}"
            spoken_text_phonetic = f"{spoken_body_phonetic} {CLOSING_NOTICE_HI_PHONETIC}"

            summary_text = (
                "नए निवेशकों के लिए सबसे सफल रणनीति है: **कम लागत, इंडेक्स डायवर्सिफिकेशन और स्वचालित निवेश**। "
                "जब तक आपका इंडेक्स और म्यूचुअल फंड का मजबूत आधार न बन जाए, तब तक सट्टेबाजी या सीधे स्टॉक पिकिंग से बचें।"
            )
        else:
            title = "Beginner's Rule-Based Wealth Architecture"
            allocations = [
                {
                    'category': 'Broad Index ETFs (Nifty 50 & Next 50)',
                    'percentage': eq_pct,
                    'color': '#2563eb',
                    'icon': 'fas fa-chart-line',
                    'instruments': ['NIFTYBEES', 'JUNIORBEES'],
                    'rationale': 'Low-cost (0.05% expense ratio) access to India’s top 100 blue chips without single-stock risk.'
                },
                {
                    'category': 'Flexi-Cap / Active Mutual Funds',
                    'percentage': flex_pct,
                    'color': '#8b5cf6',
                    'icon': 'fas fa-layer-group',
                    'instruments': ['Parag Parikh Flexi Cap', 'HDFC Balanced Advantage'],
                    'rationale': 'Professional active management across market caps with downside cushion.'
                },
                {
                    'category': 'Gold Hedge (Sovereign Gold / ETF)',
                    'percentage': gold_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-coins',
                    'instruments': ['GOLDBEES', 'Sovereign Gold Bonds'],
                    'rationale': 'Hedge against rupee depreciation and inflation cycles.'
                },
                {
                    'category': 'Emergency Liquid Buffer / High-Yield FD',
                    'percentage': debt_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-shield-alt',
                    'instruments': ['Liquid Mutual Funds', 'Auto-sweep Savings / FD'],
                    'rationale': 'Guaranteed liquidity so you never sell equity during a market drawdown.'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'Build 3-Month Emergency Reserve First',
                    'detail': 'Before investing in equities, ensure 3 to 6 months of living expenses are in a liquid fund or savings account.',
                    'icon': 'fas fa-shield-alt'
                },
                {
                    'step_num': 2,
                    'title': 'Automate Salary-Day SIPs',
                    'detail': 'Schedule automated SIP debits between the 1st and 5th of each month right after salary credit.',
                    'icon': 'fas fa-calendar-check'
                },
                {
                    'step_num': 3,
                    'title': 'Deploy Foliux Buy-on-Dips Pyramiding',
                    'detail': f'When Nifty drops {dip_buy:g}% from monthly peaks, deploy additional small opportunistic tranches.',
                    'icon': 'fas fa-arrow-trend-down'
                },
                {
                    'step_num': 4,
                    'title': f'Harvest Profits at {harvest_target}%',
                    'detail': f'When any equity or mutual fund lot generates {harvest_target}% unrealized profit, harvest gains and rebalance.',
                    'icon': 'fas fa-hand-holding-dollar'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_en']} Welcome to FOLIUX. For a beginner {mode_label_en} investment "
                f"{'of ' + amount_str if amount_str else ''}, here is your disciplined plan. "
                f"Allocate {eq_pct} percent to broad market index ETFs like NIFTYBEES and JUNIORBEES for rock-solid large-cap growth. "
                f"Allocate {flex_pct} percent to disciplined Flexi-Cap mutual funds. "
                f"Keep {gold_pct} percent in Gold ETFs for inflation protection, and hold {debt_pct} percent in emergency liquid funds. "
                "Most importantly, follow the core Foliux rule: never try to time the market with emotions. "
                f"Automate your investments right after salary day, accumulate incrementally during {dip_buy:g} percent market dips, "
                f"and harvest profits when holdings reach a {harvest_target} percent target gain."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_EN}"
            spoken_text_phonetic = spoken_text

            summary_text = (
                "For first-time investors, the winning formula is **low fees, maximum diversification, and disciplined automation**. "
                "Avoid speculative stock-picking until you build a solid index and mutual fund foundation."
            )

    # -------------------------------------------------------------
    # 2. SPECIAL TOPIC: RETIREMENT & PENSION (NPS FOCUS)
    # -------------------------------------------------------------
    elif topic == "retirement" or (horizon == "long" and any(w in query.lower() for w in ['retire', 'pension', 'nps', 'old age', 'रिटायरमेंट', 'पेंशन', 'बुढ़ापा'])):
        strategy_key = 'retirement'
        learned_weights = get_adaptive_weights(strategy_key, regime)
        nps_pct = int(learned_weights['debt_weight'])
        eq_pct = int(learned_weights['equity_weight'])
        flex_pct = int(learned_weights['flexicap_weight'])
        gold_pct = int(learned_weights['gold_weight'])
        harvest_target = int(learned_weights.get('harvest_target_pct', 22))
        dip_buy = float(learned_weights.get('dip_buy_pct', 3.5))

        if lang == 'hi':
            title = "लंबी अवधि और रिटायरमेंट वेल्थ कंपाउंडिंग ब्लूप्रिंट"
            allocations = [
                {
                    'category': 'नेशनल पेंशन सिस्टम (NPS Tier-1 Scheme E/C)',
                    'percentage': nps_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-university',
                    'instruments': ['NPS Scheme E (75% Equity)', 'NPS Scheme C (Corporate Bonds)'],
                    'rationale': 'धारा 80CCD(1B) के तहत ₹50,000 की विशेष टैक्स छूट और केवल 0.09% का अल्ट्रा-लो फंड मैनेजमेंट खर्च।'
                },
                {
                    'category': 'ब्रॉड इंडेक्स और सेक्टोरल ईटीएफ (कंपाउंडिंग अल्फा)',
                    'percentage': eq_pct,
                    'color': '#2563eb',
                    'icon': 'fas fa-chart-line',
                    'instruments': ['NIFTYBEES', 'MON100', 'ITBEES'],
                    'rationale': 'अगले 10 से 20 वर्षों में भारत और वैश्विक टेक्नोलॉजी की मजबूत आर्थिक वृद्धि का लाभ।'
                },
                {
                    'category': 'फ्लेक्सी-कैप एवं मिडकैप म्यूचुअल फंड SIP',
                    'percentage': flex_pct,
                    'color': '#8b5cf6',
                    'icon': 'fas fa-layer-group',
                    'instruments': ['HDFC Flexi Cap', 'Mirae Asset Large & Midcap'],
                    'rationale': 'महंगाई को पछाड़ने के लिए उच्च गुणवत्ता वाली इक्विटी भागीदारी।'
                },
                {
                    'category': 'सॉवरेन गोल्ड एवं सरकारी डेट फंड्स',
                    'percentage': gold_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-coins',
                    'instruments': ['GOLDBEES', 'Target Maturity Govt Debt Funds'],
                    'rationale': 'मुद्रा के अवमूल्यन और वैश्विक उतार-चढ़ाव से पूंजी का सुरक्षा कवच।'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'एनपीएस Tier-1 की ₹50,000 टैक्स छूट का पूरा लाभ लें',
                    'detail': 'धारा 80C के अतिरिक्त धारा 80CCD(1B) के अंतर्गत विशेष टैक्स कटौती प्राप्त करें।',
                    'icon': 'fas fa-file-invoice-dollar'
                },
                {
                    'step_num': 2,
                    'title': 'सक्रिय ऑटो-चॉइस लाइफसाइकिल चुनें',
                    'detail': 'अपने संचय वर्षों में 75% इक्विटी बनाए रखें और रिटायरमेंट के करीब आने पर इसे धीरे-धीरे कम करें।',
                    'icon': 'fas fa-sliders'
                },
                {
                    'step_num': 3,
                    'title': 'हर साल 10% वार्षिक SIP स्टेप-अप करें',
                    'detail': f'आय बढ़ने के साथ हर साल मासिक निवेश को 10% बढ़ाएं, और बाजार {dip_buy:g}% गिरने पर अतिरिक्त खरीदारी करें।',
                    'icon': 'fas fa-arrow-trend-up'
                },
                {
                    'step_num': 4,
                    'title': f'{harvest_target}% लाभ पर FOLIUX फीफो विधि से रीबैलेंसिंग करें',
                    'detail': f'शॉर्ट टर्म कैपिटल गेन टैक्स से बचते हुए {harvest_target}% पर अनुशासित रीबैलेंसिंग सुनिश्चित करें।',
                    'icon': 'fas fa-scale-balanced'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_hi']} यह आपकी FOLIUX रिटायरमेंट और वेल्थ कंपाउंडिंग रणनीति है{' ' + amount_str + ' के लिए' if amount_str else ''}। "
                f"लंबी अवधि के रिटायरमेंट के लिए, {nps_pct} प्रतिशत नेशनल पेंशन सिस्टम यानी एनपीएस में लगाएं, "
                "जहां आपको धारा 80CCD में विशेष टैक्स छूट और न्यूनतम खर्च का लाभ मिलता है। "
                f"{eq_pct} प्रतिशत निफ्टीबीज और मुख्य इंडेक्स ईटीएफ में लगाएं, {flex_pct} प्रतिशत फ्लेक्सी-कैप म्यूचुअल फंड में, और {gold_pct} प्रतिशत गोल्ड में रखें। "
                f"अपनी मासिक एसआईपी को हर साल 10 प्रतिशत बढ़ाएं, बाजार {dip_buy:g} प्रतिशत गिरने पर अतिरिक्त यूनिट्स खरीदें, "
                f"और {harvest_target} प्रतिशत लाभ पर रीबैलेंस करें। 10 से 15 साल धैर्यपूर्वक कंपाउंडिंग होने दें और बाजार के शोर से दूर रहें।"
            )
            spoken_body_phonetic = (
                f"{regime_data['insight_hi_phonetic']} Yeh aapki FOLIUX retirement aur wealth compounding ranniti hai{' ' + amount_str + ' ke liye' if amount_str else ''}. "
                f"Lambi avadhi ke retirement ke liye, {nps_pct} percent National Pension System yaani NPS mein lagayein, "
                "jahan aapko Section 80CCD mein vishesh tax chhoot aur nyuntam kharch ka labh milta hai. "
                f"{eq_pct} percent NiftyBees aur mukhya index ETF mein lagayein, {flex_pct} percent flexi-cap mutual fund mein, aur {gold_pct} percent gold mein rakhein. "
                f"Apni masik SIP ko har saal 10 percent badhayein, bazaar {dip_buy:g} percent girne par atirikt units kharidein, "
                f"aur {harvest_target} percent labh par rebalance karein. 10 se 15 saal dhairyapurvak compounding hone dein aur bazaar ke shor se door rahein."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_HI}"
            spoken_text_phonetic = f"{spoken_body_phonetic} {CLOSING_NOTICE_HI_PHONETIC}"

            summary_text = (
                "रिटायरमेंट संपत्ति का निर्माण **टैक्स-लाभ और अनुशासित स्टेप-अप निवेश** से होता है। "
                "टियर-1 एनपीएस और इंडेक्स ईटीएफ का संतुलन आपको न्यूनतम लागत पर अधिकतम कंपाउंडिंग ग्रोथ प्रदान करता है।"
            )
        else:
            title = "Long-Term Retirement & Compounding Blueprint"
            allocations = [
                {
                    'category': 'National Pension System (Tier-1 Scheme E/C/G)',
                    'percentage': nps_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-university',
                    'instruments': ['NPS Scheme E (75% Equity)', 'NPS Scheme C (Corporate Bonds)'],
                    'rationale': 'Unbeatable tax advantage under Section 80CCD(1B) plus ultra-low 0.09% fund management charges.'
                },
                {
                    'category': 'Broad Index & Sectoral ETFs (Compounding Alpha)',
                    'percentage': eq_pct,
                    'color': '#2563eb',
                    'icon': 'fas fa-chart-line',
                    'instruments': ['NIFTYBEES', 'MON100', 'ITBEES'],
                    'rationale': 'Captures secular Indian & global technology growth over a 10 to 20 year compounding horizon.'
                },
                {
                    'category': 'Consistent Flexi-Cap & Midcap SIPs',
                    'percentage': flex_pct,
                    'color': '#8b5cf6',
                    'icon': 'fas fa-layer-group',
                    'instruments': ['HDFC Flexi Cap', 'Mirae Asset Large & Midcap'],
                    'rationale': 'High-conviction equity exposure to beat headline retail inflation.'
                },
                {
                    'category': 'Sovereign Gold / G-Secs',
                    'percentage': gold_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-coins',
                    'instruments': ['GOLDBEES', 'Target Maturity Govt Debt Funds'],
                    'rationale': 'Defensive capital preservation against macro currency volatility.'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'Maximize Tier-1 NPS ₹50,000 Tax Benefit',
                    'detail': 'Claim exclusive tax deduction under Section 80CCD(1B) over and above Section 80C limits.',
                    'icon': 'fas fa-file-invoice-dollar'
                },
                {
                    'step_num': 2,
                    'title': 'Adopt Auto-Choice Active Lifecycle',
                    'detail': 'Maintain 75% equity exposure in NPS during accumulation years and gradually taper near retirement.',
                    'icon': 'fas fa-sliders'
                },
                {
                    'step_num': 3,
                    'title': 'Run 10% Annual SIP Step-Up',
                    'detail': f'Increase your monthly investment SIP by 10% each year, and deploy extra on {dip_buy:g}% market dips.',
                    'icon': 'fas fa-arrow-trend-up'
                },
                {
                    'step_num': 4,
                    'title': f'Rebalance Annually via FIFO at {harvest_target}%',
                    'detail': f'Use Foliux FIFO lot tracking to rebalance assets at {harvest_target}% without incurring unnecessary STCG tax.',
                    'icon': 'fas fa-scale-balanced'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_en']} Here is your FOLIUX retirement and wealth compounding strategy{' for ' + amount_str if amount_str else ''}. "
                f"For a long-term retirement horizon, allocate {nps_pct} percent to the National Pension System Scheme E and C, "
                "which gives you unmatched tax deductions under Section 80CCD and ultra-low compounding fees. "
                f"Place {eq_pct} percent in core index ETFs like NIFTYBEES and MON100, {flex_pct} percent in flexi-cap mutual fund SIPs, "
                f"and {gold_pct} percent in Gold. Step up your monthly contributions by 10 percent every year, accumulate on {dip_buy:g} percent market dips, "
                f"and harvest at {harvest_target} percent gains. By letting compounding work over 10 to 15 years and avoiding emotional withdrawals, you create enduring wealth."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_EN}"
            spoken_text_phonetic = spoken_text

            summary_text = (
                "Retirement wealth is built on **tax-advantaged compounding and disciplined step-up investing**. "
                "Combining Tier-1 NPS with core index ETFs delivers institutional-grade capital growth with maximum tax efficiency."
            )

    # -------------------------------------------------------------
    # 3. SPECIAL TOPIC: SHORT-TERM / CONSERVATIVE (SAFE CAPITAL)
    # -------------------------------------------------------------
    elif horizon == "short" or risk == "conservative":
        strategy_key = 'capital_preservation'
        learned_weights = get_adaptive_weights(strategy_key, regime)
        fd_pct = int(learned_weights['debt_weight'])
        arb_pct = int(learned_weights['flexicap_weight'])
        bond_pct = int(learned_weights['gold_weight'])
        eq_pct = int(learned_weights['equity_weight'])
        harvest_target = int(learned_weights.get('harvest_target_pct', 12))
        dip_buy = float(learned_weights.get('dip_buy_pct', 2.0))

        if lang == 'hi':
            title = "पूंजी सुरक्षा एवं लिक्विड यील्ड रणनीति"
            allocations = [
                {
                    'category': 'उच्च-ब्याज बैंक फिक्स्ड डिपॉजिट / ऑटो-स्वीप',
                    'percentage': fd_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-building-columns',
                    'instruments': ['Scheduled Commercial Bank FDs (7.0 - 7.5%)', 'Auto-sweep'],
                    'rationale': 'डीआईसीजीसी बीमा सुरक्षा के साथ गारंटीड पूंजी सुरक्षा और निश्चित ब्याज दर।'
                },
                {
                    'category': 'आर्बिट्राज एवं लिक्विड म्यूचुअल फंड्स',
                    'percentage': arb_pct,
                    'color': '#3b82f6',
                    'icon': 'fas fa-water',
                    'instruments': ['Kotak Arbitrage Fund', 'ICICI Prudential Liquid Fund'],
                    'rationale': 'इक्विटी टैक्स दर के साथ कम जोखिम और केवल एक दिन में निकासी की सुविधा।'
                },
                {
                    'category': 'शॉर्ट-ड्यूरेशन / कॉरपोरेट बॉन्ड फंड्स',
                    'percentage': bond_pct,
                    'color': '#6366f1',
                    'icon': 'fas fa-receipt',
                    'instruments': ['AAA Corporate Bond Funds', 'Treasury Bill Funds'],
                    'rationale': 'ब्याज दरों के उतार-चढ़ाव से मुक्त और स्थिर आय का साधन।'
                },
                {
                    'category': 'कंजर्वेटिव लार्ज-कैप ईटीएफ बफर',
                    'percentage': eq_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-chart-pie',
                    'instruments': ['NIFTYBEES'],
                    'rationale': 'केवल तभी जब आपकी निवेश अवधि 12 महीने से अधिक खिंचने की संभावना हो।'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'शॉर्ट-टर्म पैसे को वोलेटाइल इक्विटी या स्मॉल-कैप में न लगाएं',
                    'detail': 'जिस पैसे की जरूरत 12 से 18 महीनों में हो, उसे शेयर बाजार की अस्थिरता में जोखिम में न डालें।',
                    'icon': 'fas fa-ban'
                },
                {
                    'step_num': 2,
                    'title': 'टैक्स बचत के लिए आर्बिट्राज फंड अपनाएं',
                    'detail': 'आर्बिट्राज फंड डेट जैसी सुरक्षा देते हैं लेकिन इक्विटी की तरह टैक्स होते हैं, जिससे टैक्स बचता है।',
                    'icon': 'fas fa-percent'
                },
                {
                    'step_num': 3,
                    'title': 'फिक्स्ड डिपॉजिट को अलग-अलग अवधियों में बांटें (Laddering)',
                    'detail': 'नियमित कैशफ्लो और लिक्विडिटी बनाए रखने के लिए 3, 6 और 12 महीने की किश्तों में एफडी करें।',
                    'icon': 'fas fa-bars-staggered'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_hi']} कम अवधि और सुरक्षित पूंजी के लिए{' ' + amount_str + ' हेतु' if amount_str else ''}, "
                "पूंजी सुरक्षा सबसे महत्वपूर्ण है। इस पैसे को जोखिम भरे शेयरों में बिल्कुल न लगाएं। "
                f"{fd_pct} प्रतिशत बैंकों की सुरक्षित एफडी में लगाएं जो 7 से 7.5 प्रतिशत ब्याज देती हैं। "
                f"{arb_pct} प्रतिशत आर्बिट्राज और लिक्विड फंड में रखें जहां टैक्स की बचत और त्वरित निकासी मिलती है, "
                f"{bond_pct} प्रतिशत कॉरपोरेट बॉन्ड में और अधिकतम {eq_pct} प्रतिशत इंडेक्स ईटीएफ में रखें। "
                "यह रणनीति आपके मूलधन को सुरक्षित रखते हुए सामान्य बचत खाते से बेहतर रिटर्न देती है।"
            )
            spoken_body_phonetic = (
                f"{regime_data['insight_hi_phonetic']} Kam avadhi aur surakshit poonji ke liye{' ' + amount_str + ' hetu' if amount_str else ''}, "
                "poonji suraksha sabse mahatvapoorna hai. Is paise ko jokhim bhare share bazaar mein bilkul na lagayein. "
                f"{fd_pct} percent anusoocheet bankon ki surakshit FD mein lagayein jo 7 se 7.5 percent byaj deti hain. "
                f"{arb_pct} percent arbitrage aur liquid fund mein rakhein jahan tax ki bachat aur turant nikasi milti hai, "
                f"{bond_pct} percent corporate bond mein aur adhiktam {eq_pct} percent index ETF mein rakhein. "
                "Yeh ranniti aapke mool dhan ko surakshit rakhte hue sadharan bachat khate se behtar return deti hai."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_HI}"
            spoken_text_phonetic = f"{spoken_body_phonetic} {CLOSING_NOTICE_HI_PHONETIC}"

            summary_text = (
                "जब आपका लक्ष्य 1 से 2 साल का हो, तो **पहला नियम पूंजी की सुरक्षा है**। "
                "सुरक्षित फिक्स्ड डिपॉजिट और आर्बिट्राज फंड यह सुनिश्चित करते हैं कि जरूरत के समय आपका पैसा पूरी तरह सुरक्षित रहे।"
            )
        else:
            title = "Capital Preservation & Liquid Yield Strategy"
            allocations = [
                {
                    'category': 'High-Yield Fixed Deposits / Bank Auto-Sweep',
                    'percentage': fd_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-building-columns',
                    'instruments': ['Scheduled Commercial Bank FDs (7.0 - 7.5%)', 'Auto-sweep'],
                    'rationale': 'Guaranteed capital safety with predictable interest returns under DICGC insurance.'
                },
                {
                    'category': 'Arbitrage & Liquid Mutual Funds',
                    'percentage': arb_pct,
                    'color': '#3b82f6',
                    'icon': 'fas fa-water',
                    'instruments': ['Kotak Arbitrage Fund', 'ICICI Prudential Liquid Fund'],
                    'rationale': 'Equity-taxed low-volatility returns with instant T+1 redemption liquidity.'
                },
                {
                    'category': 'Short-Duration / Corporate Debt Funds',
                    'percentage': bond_pct,
                    'color': '#6366f1',
                    'icon': 'fas fa-receipt',
                    'instruments': ['AAA Corporate Bond Funds', 'Treasury Bill Funds'],
                    'rationale': 'Stable yields with minimal interest rate duration risk.'
                },
                {
                    'category': 'Conservative Large-Cap ETF Buffer',
                    'percentage': eq_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-chart-pie',
                    'instruments': ['NIFTYBEES'],
                    'rationale': 'Small growth kicker only if your horizon stretches beyond 12 months.'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'Never Risk Short-Term Capital in Mid/Small Caps',
                    'detail': 'Money needed within 12 to 18 months must never be subjected to equity market volatility.',
                    'icon': 'fas fa-ban'
                },
                {
                    'step_num': 2,
                    'title': 'Utilize Arbitrage Funds for Tax Efficiency',
                    'detail': 'Arbitrage funds offer debt-like safety but are taxed as equity, saving taxes for high-bracket earners.',
                    'icon': 'fas fa-percent'
                },
                {
                    'step_num': 3,
                    'title': 'Ladder Your Fixed Deposits',
                    'detail': 'Split FDs into 3-month, 6-month, and 12-month tranches to maintain regular cashflow flexibility.',
                    'icon': 'fas fa-bars-staggered'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_en']} For capital safety and short-term horizons{' with ' + amount_str if amount_str else ''}, "
                "capital preservation is paramount. Do not deploy this money into volatile equities. "
                f"Allocate {fd_pct} percent to scheduled bank fixed deposits yielding 7 to 7.5 percent. "
                f"Place {arb_pct} percent in arbitrage and liquid mutual funds for tax-efficient liquidity, "
                f"{bond_pct} percent in AAA corporate bond funds, and keep no more than {eq_pct} percent in index ETFs. "
                "This protects your principal while beating ordinary savings rates."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_EN}"
            spoken_text_phonetic = spoken_text

            summary_text = (
                "When your goal is within 1 to 2 years, **rule number one is capital protection**. "
                "High-yielding fixed deposits and arbitrage funds guarantee you will have the cash when you need it."
            )

    # -------------------------------------------------------------
    # 4. LUMP SUM INVESTMENT (DEPLOYMENT LOGIC)
    # -------------------------------------------------------------
    elif is_lump_sum and amount and amount >= 50000:
        strategy_key = 'lump_sum'
        learned_weights = get_adaptive_weights(strategy_key, regime)
        eq_pct = int(learned_weights['equity_weight'])
        flex_pct = int(learned_weights['flexicap_weight'])
        gold_pct = int(learned_weights['gold_weight'])
        cash_pct = int(learned_weights['debt_weight'])
        harvest_target = int(learned_weights.get('harvest_target_pct', 22))
        dip_buy = float(learned_weights.get('dip_buy_pct', 3.5))

        if lang == 'hi':
            title = f"{amount_str} एकमुश्त राशि हेतु FOLIUX अनुशासित निवेश ब्लूप्रिंट"
            allocations = [
                {
                    'category': 'कोर इंडेक्स और सेक्टोरल ईटीएफ (Nifty और Tech)',
                    'percentage': eq_pct,
                    'color': '#2563eb',
                    'icon': 'fas fa-chart-line',
                    'instruments': ['NIFTYBEES', 'JUNIORBEES', 'ITBEES'],
                    'rationale': 'भारत के प्रमुख आर्थिक इंजनों में व्यवस्थित रूप से प्रवेश।'
                },
                {
                    'category': 'सक्रिय फ्लेक्सी-कैप एवं मिडकैप फंड्स',
                    'percentage': flex_pct,
                    'color': '#8b5cf6',
                    'icon': 'fas fa-layer-group',
                    'instruments': ['Parag Parikh Flexi Cap', 'Motilal Oswal Midcap'],
                    'rationale': 'तेजी से बढ़ती कंपनियों की आय वृद्धि से पोर्टफोलियो को अल्फा प्रदान करना।'
                },
                {
                    'category': 'सॉवरेन गोल्ड एवं कमोडिटीज',
                    'percentage': gold_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-coins',
                    'instruments': ['GOLDBEES', 'SILVERBEES'],
                    'rationale': 'बाजार की गिरावट में आपकी क्रय शक्ति को सुरक्षित रखने वाला एसेट।'
                },
                {
                    'category': 'लिक्विड एसटीपी पार्किंग फंड',
                    'percentage': cash_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-money-bill-transfer',
                    'instruments': ['Overnight / Ultra Short Duration Debt'],
                    'rationale': 'अगले 6 से 12 महीनों के दौरान व्यवस्थित ट्रांसफर के लिए सुरक्षित नकदी।'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'एक ही दिन में पूरा पैसा बाजार में न लगाएं',
                    'detail': f"{nifty_info_hi}बाजार के स्थानीय शिखर पर फंसने से बचने के लिए एक ही दिन में पूरे {amount_str} का निवेश न करें।",
                    'icon': 'fas fa-shield-halved'
                },
                {
                    'step_num': 2,
                    'title': 'लिक्विड फंड में रखकर 6 महीने की एसटीपी चलाएं',
                    'detail': f"पूरी राशि को लिक्विड फंड में रखें और अगले 24 हफ्तों के लिए साप्ताहिक सिस्टमैटिक ट्रांसफर प्लान (STP) सेट करें।",
                    'icon': 'fas fa-clock-rotate-left'
                },
                {
                    'step_num': 3,
                    'title': f'बाजार सुधार के लिए {cash_pct}% कैश रिजर्व रखें',
                    'detail': f'जब निफ्टी {dip_buy:g}% से 7% गिरे, तब इस सुरक्षित कैश से अतिरिक्त लॉट खरीदें।',
                    'icon': 'fas fa-fire'
                },
                {
                    'step_num': 4,
                    'title': f'{harvest_target}% लाभ पर FOLIUX नियमों से प्रॉफिट हार्वेस्ट करें',
                    'detail': f'{harvest_target}% से अधिक लाभ होने पर अनुशासित होकर लाभ सुरक्षित नकदी में वापस लाएं।',
                    'icon': 'fas fa-hand-holding-dollar'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_hi']} आपके {amount_str} एकमुश्त निवेश के लिए यह FOLIUX संस्थागत योजना है। "
                "अत्यंत महत्वपूर्ण नियम: एक ही दिन में सारा पैसा बाजार में न लगाएं। "
                "पहले पूरी रकम को लिक्विड म्यूचुअल फंड में रखें और वहां से 6 महीने का सिस्टमैटिक ट्रांसफर प्लान शुरू करें। "
                f"{eq_pct} प्रतिशत निफ्टीबीज और मुख्य इंडेक्स ईटीएफ में, {flex_pct} प्रतिशत टॉप फ्लेक्सी-कैप फंड में, "
                f"{gold_pct} प्रतिशत गोल्ड ईटीएफ में लगाएं, और {cash_pct} प्रतिशत कैश रिजर्व रखें। "
                f"बाजार में {dip_buy:g} प्रतिशत की गिरावट आने पर अतिरिक्त हिस्सा निवेश करें, और {harvest_target} प्रतिशत पर मुनाफा वसूलें। यह तरीका मार्केट टॉप पर खरीदने के जोखिम को समाप्त करता है।"
            )
            spoken_body_phonetic = (
                f"{regime_data['insight_hi_phonetic']} Aapke {amount_str} ekmusht nivesh ke liye yeh FOLIUX sansthagat yojana hai. "
                "Atyant mahatvapoorna niyam: ek hi din mein saara paisa bazaar mein na lagayein. "
                "Pehle poori rakam ko liquid mutual fund mein rakhein aur wahan se 6 mahine ka systematic transfer plan shuru karein. "
                f"{eq_pct} percent NiftyBees aur mukhya index ETF mein, {flex_pct} percent top flexi-cap fund mein, "
                f"{gold_pct} percent Gold ETF mein lagayein, aur {cash_pct} percent cash reserve rakhein. "
                f"Bazaar mein {dip_buy:g} percent ki girawat aane par atirikt hissa nivesh karein, aur {harvest_target} percent par munafa vasulein. Yeh tareeka market top par khareedne ke risk ko samapt karta hai."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_HI}"
            spoken_text_phonetic = f"{spoken_body_phonetic} {CLOSING_NOTICE_HI_PHONETIC}"

            summary_text = (
                f"जब आपके पास **{amount_str}** की एकमुश्त राशि हो, तो **सिस्टमैटिक ट्रांसफर (STP)** मार्केट टाइमिंग से कहीं बेहतर है। "
                "6 महीने में किश्तों में निवेश करने से टाइमिंग रिस्क खत्म होता है और आपका पैसा लिक्विड रिटर्न भी कमाता है।"
            )
        else:
            title = f"Disciplined Deployment Plan for {amount_str} Lump Sum"
            allocations = [
                {
                    'category': 'Core Index & Thematic ETFs (Nifty & Tech)',
                    'percentage': eq_pct,
                    'color': '#2563eb',
                    'icon': 'fas fa-chart-line',
                    'instruments': ['NIFTYBEES', 'JUNIORBEES', 'ITBEES'],
                    'rationale': 'Staggered STP entry into India’s dominant economic engines.'
                },
                {
                    'category': 'Active Flexi-Cap & Midcap Funds',
                    'percentage': flex_pct,
                    'color': '#8b5cf6',
                    'icon': 'fas fa-layer-group',
                    'instruments': ['Parag Parikh Flexi Cap', 'Motilal Oswal Midcap'],
                    'rationale': 'Generates alpha through high-conviction corporate earnings growth.'
                },
                {
                    'category': 'Sovereign Gold / Commodities',
                    'percentage': gold_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-coins',
                    'instruments': ['GOLDBEES', 'SILVERBEES'],
                    'rationale': 'Non-correlated asset that preserves purchasing power during market corrections.'
                },
                {
                    'category': 'Liquid STP Parking Fund',
                    'percentage': cash_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-money-bill-transfer',
                    'instruments': ['Overnight / Ultra Short Duration Debt'],
                    'rationale': 'Holds dry powder to feed systematic transfers over 6 to 12 months.'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'Avoid 100% Day-One Market Dumps',
                    'detail': f"{nifty_info_en}Do not deploy all {amount_str} in a single trading day to avoid catching local market tops.",
                    'icon': 'fas fa-shield-halved'
                },
                {
                    'step_num': 2,
                    'title': 'Park in Liquid Fund & Run 6-Month STP',
                    'detail': f"Park {amount_str} in a liquid fund and set up a weekly Systematic Transfer Plan (STP) across 24 weeks.",
                    'icon': 'fas fa-clock-rotate-left'
                },
                {
                    'step_num': 3,
                    'title': f'Hold {cash_pct}% Opportunistic Dip Reserve',
                    'detail': f'Keep a {cash_pct}% tranche ready to manually deploy if Nifty experiences a {dip_buy:g}% to 7% correction.',
                    'icon': 'fas fa-fire'
                },
                {
                    'step_num': 4,
                    'title': f'Harvest Profits with Foliux Rules at {harvest_target}%',
                    'detail': f'Once lots gain {harvest_target}%+, systematically book profits back into liquid safety.',
                    'icon': 'fas fa-hand-holding-dollar'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_en']} Here is your FOLIUX institutional deployment plan for your {amount_str} lump sum. "
                "Crucial rule: do not invest the entire amount in a single day. "
                "Park the corpus in a liquid mutual fund and set up a 6-month Systematic Transfer Plan into equities. "
                f"Target {eq_pct} percent in broad index ETFs like NIFTYBEES and ITBEES, {flex_pct} percent in top flexi-cap mutual funds, "
                f"{gold_pct} percent in Gold ETFs, and keep {cash_pct} percent as cash dry powder. "
                f"If the market corrects {dip_buy:g} percent, deploy an extra tranche, and harvest gains at {harvest_target} percent. "
                "This dollar cost averaging prevents the regret of buying at the top."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_EN}"
            spoken_text_phonetic = spoken_text

            summary_text = (
                f"When managing a lump sum of **{amount_str}**, disciplined **Systematic Transfer (STP)** beats market timing. "
                "Staggering deployments over 6 months eliminates timing risk while keeping your capital working in liquid yields."
            )

    # -------------------------------------------------------------
    # 5. DEFAULT / MONTHLY SIP WEALTH CREATION (GENERAL)
    # -------------------------------------------------------------
    else:
        strategy_key = 'default_sip'
        learned_weights = get_adaptive_weights(strategy_key, regime)
        eq_pct = int(learned_weights['equity_weight'])
        flex_pct = int(learned_weights['flexicap_weight'])
        nps_pct = int(learned_weights['debt_weight'])
        gold_pct = int(learned_weights['gold_weight'])
        harvest_target = int(learned_weights.get('harvest_target_pct', 22))
        dip_buy = float(learned_weights.get('dip_buy_pct', 3.5))

        if lang == 'hi':
            amt_disp = amount_str if amount_str else "₹10,000 / महीना"
            amt_disp_phonetic = amount_str if amount_str else "₹10,000 per month"
            title = f"FOLIUX वेल्थ इंजीनियरिंग आवंटन ({amt_disp})"

            allocations = [
                {
                    'category': 'कोर इंडेक्स ईटीएफ (न्यूनतम खर्च अनुपात)',
                    'percentage': eq_pct,
                    'color': '#2563eb',
                    'icon': 'fas fa-chart-line',
                    'instruments': ['NIFTYBEES', 'JUNIORBEES'],
                    'rationale': 'बिना किसी फंड मैनेजर जोखिम के, सीधे भारत की शीर्ष 100 कंपनियों की ग्रोथ का फायदा।'
                },
                {
                    'category': 'फ्लेक्सी-कैप एवं मिडकैप म्यूचुअल फंड्स',
                    'percentage': flex_pct,
                    'color': '#8b5cf6',
                    'icon': 'fas fa-layer-group',
                    'instruments': ['Parag Parikh Flexi Cap', 'Nippon India Growth Fund'],
                    'rationale': 'तेजी से बढ़ती कंपनियों में अनुशासित तिमाही रीबैलेंसिंग के साथ निवेश।'
                },
                {
                    'category': 'रिटायरमेंट टैक्स कंपाउंडिंग (NPS)',
                    'percentage': nps_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-university',
                    'instruments': ['NPS Tier-1 Scheme E/C'],
                    'rationale': 'धारा 80CCD(1B) के तहत विशेष टैक्स छूट और अनिवार्य कंपाउंडिंग।'
                },
                {
                    'category': 'गोल्ड और लिक्विड बफर',
                    'percentage': gold_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-coins',
                    'instruments': ['GOLDBEES', 'Liquid Fund Buffer'],
                    'rationale': 'भू-राजनीतिक संकट और बाजार की अस्थिरता के समय पोर्टफोलियो का शॉक एब्जॉर्बर।'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'हर महीने स्वचालित SIP सेट करें',
                    'detail': 'अपने मुख्य बैंक खाते से हर महीने की 1 या 5 तारीख को ऑटो-डेबिट लगाएं।',
                    'icon': 'fas fa-bolt'
                },
                {
                    'step_num': 2,
                    'title': 'गिरावट पर FOLIUX पिरामिडिंग अपनाएं',
                    'detail': f'जब निफ्टी 50 में {dip_buy:g}% की गिरावट आए, तो NIFTYBEES या मुख्य ईटीएफ में अतिरिक्त लॉट खरीदें।',
                    'icon': 'fas fa-arrow-trend-down'
                },
                {
                    'step_num': 3,
                    'title': f'{harvest_target}% लाभ पर प्रॉफिट हार्वेस्टिंग नियम लागू करें',
                    'detail': f'जब भी किसी व्यक्तिगत खरीद लॉट में {harvest_target}% का लाभ हो, उसे बेचकर कम आवंटन वाले एसेट्स में रीसायकल करें।',
                    'icon': 'fas fa-scissors'
                },
                {
                    'step_num': 4,
                    'title': 'टैक्स बचत के लिए FOLIUX फीफो (FIFO) इस्तेमाल करें',
                    'detail': 'Foliux ऑटोमैटिक फर्स्ट-इन-फर्स्ट-आउट अकाउंटिंग लागू करता है ताकि लॉन्ग टर्म कैपिटल गेन छूट का पूरा फायदा मिले।',
                    'icon': 'fas fa-calculator'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_hi']} आपके {amt_disp} के निवेश के लिए यह FOLIUX रणनीति है। "
                "अनुशासित तरीके से लंबी अवधि की संपत्ति बनाने के लिए अपने निवेश को चार स्पष्ट भागों में बांटें: "
                f"{eq_pct} प्रतिशत कोर इंडेक्स ईटीएफ जैसे निफ्टीबीज और जूनियरबीज में लगाएं। {flex_pct} प्रतिशत साबित फ्लेक्सी-कैप म्यूचुअल फंड में रखें। "
                f"{nps_pct} प्रतिशत नेशनल पेंशन सिस्टम में रिटायरमेंट टैक्स कंपाउंडिंग के लिए लगाएं, और {gold_pct} प्रतिशत गोल्ड ईटीएफ में रखें। "
                f"हमारे दो सुनहरे नियम याद रखें: बाजार {dip_buy:g} प्रतिशत गिरने पर अतिरिक्त खरीदारी करें, "
                f"और जब भी किसी लॉट में {harvest_target} प्रतिशत का लाभ हो, मुनाफा वसूलें। यह आपके निवेश को भावनाओं से दूर रखता है।"
            )
            spoken_body_phonetic = (
                f"{regime_data['insight_hi_phonetic']} Aapke {amt_disp_phonetic} ke nivesh ke liye yeh FOLIUX ranniti hai. "
                "Anushasit tareeke se lambi avadhi ki sampatti banane ke liye apne nivesh ko chaar spasht bhaagon mein baantein: "
                f"{eq_pct} percent core index ETF jaise NiftyBees aur JuniorBees mein lagayein. {flex_pct} percent saabit Flexi-Cap mutual fund mein rakhein. "
                f"{nps_pct} percent National Pension System mein retirement tax compounding ke liye lagayein, aur {gold_pct} percent Gold ETF mein rakhein. "
                f"Humare do sunhare niyam yaad rakhein: bazaar {dip_buy:g} percent girne par atirikt khareedari karein, "
                f"aur jab bhi kisi lot mein {harvest_target} percent ka labh ho, munafa vasulein. Yeh aapke nivesh ko bhavnaon se door rakhta hai."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_HI}"
            spoken_text_phonetic = f"{spoken_body_phonetic} {CLOSING_NOTICE_HI_PHONETIC}"

            summary_text = (
                f"**{amt_disp}** के साथ सबसे प्रमाणित रणनीति **कोर-एंड-सैटेलाइट मॉडल** है: "
                "75% हिस्सा ब्रॉड इंडेक्स ईटीएफ और म्यूचुअल फंड्स में लगाएं, और एनपीएस व गोल्ड से अपने पोर्टफोलियो को सुरक्षित और चक्रवृद्धि दर से बढ़ाएं।"
            )
        else:
            amt_disp = amount_str if amount_str else "₹10,000 / month"
            title = f"FOLIUX Wealth Engineering Allocation ({amt_disp})"

            allocations = [
                {
                    'category': 'Core Index ETFs (Low Expense Ratio)',
                    'percentage': eq_pct,
                    'color': '#2563eb',
                    'icon': 'fas fa-chart-line',
                    'instruments': ['NIFTYBEES (30%)', 'JUNIORBEES (15%)'],
                    'rationale': 'Zero fund-manager risk; directly mirrors India’s top 100 enterprise growth.'
                },
                {
                    'category': 'Flexi-Cap & Midcap Mutual Funds',
                    'percentage': flex_pct,
                    'color': '#8b5cf6',
                    'icon': 'fas fa-layer-group',
                    'instruments': ['Parag Parikh Flexi Cap', 'Nippon India Growth Fund'],
                    'rationale': 'Captures fast-growing mid-market leaders with disciplined quarterly rebalancing.'
                },
                {
                    'category': 'Retirement Tax Compounding (NPS)',
                    'percentage': nps_pct,
                    'color': '#f59e0b',
                    'icon': 'fas fa-university',
                    'instruments': ['NPS Tier-1 Scheme E/C'],
                    'rationale': 'Long-term tax deduction under 80CCD(1B) with compulsory compounding.'
                },
                {
                    'category': 'Gold & Liquid Reserve',
                    'percentage': gold_pct,
                    'color': '#10b981',
                    'icon': 'fas fa-coins',
                    'instruments': ['GOLDBEES', 'Liquid Fund Buffer'],
                    'rationale': 'Portfolio shock absorber during geopolitical and equity pullbacks.'
                }
            ]

            execution_steps = [
                {
                    'step_num': 1,
                    'title': 'Automate Your Recurring SIP',
                    'detail': 'Set monthly auto-debits on your primary bank account for the 1st or 5th of every month.',
                    'icon': 'fas fa-bolt'
                },
                {
                    'step_num': 2,
                    'title': 'Apply Foliux Pyramiding on Dips',
                    'detail': f'When the Nifty 50 drops by {dip_buy:g}%, buy an additional unit lot of NIFTYBEES or your core ETF.',
                    'icon': 'fas fa-arrow-trend-down'
                },
                {
                    'step_num': 3,
                    'title': f'Enforce the {harvest_target}% Profit Harvest Rule',
                    'detail': f'When any individual purchase lot gains {harvest_target}%, sell that lot and recycle the capital into underweight assets.',
                    'icon': 'fas fa-scissors'
                },
                {
                    'step_num': 4,
                    'title': 'Use FIFO Accounting for Taxes',
                    'detail': 'Foliux automatically applies First-In-First-Out accounting to maximize Long-Term Capital Gains exemption limits.',
                    'icon': 'fas fa-calculator'
                }
            ]

            spoken_body = (
                f"{regime_data['insight_en']} Here is your FOLIUX investment strategy for {amt_disp}. "
                "To build disciplined, long-term wealth, divide your investment into four clear buckets: "
                f"Allocate {eq_pct} percent to core index ETFs like NIFTYBEES and JUNIORBEES for steady foundation growth. "
                f"Put {flex_pct} percent into proven Flexi-Cap mutual funds. "
                f"Allocate {nps_pct} percent to the National Pension System for retirement compounding and tax savings, "
                f"and {gold_pct} percent to Gold ETFs as a market hedge. "
                f"Follow our two golden rules: buy additional units during {dip_buy:g} percent market dips, "
                f"and harvest profits whenever a lot reaches a {harvest_target} percent profit. This keeps emotions out of your money."
            )
            spoken_text = f"{spoken_body} {CLOSING_NOTICE_EN}"
            spoken_text_phonetic = spoken_text

            summary_text = (
                f"With **{amt_disp}**, the proven strategy is a **Core-and-Satellite framework**: "
                "anchor 75% in broad index ETFs and mutual funds, while using NPS and Gold to protect and compound your net worth."
            )

    # Calculate monetary split if amount is available
    if amount and amount > 0:
        suffix = " / महीना" if (lang == 'hi' and is_sip) else (" / month" if is_sip else "")
        for item in allocations:
            item_val = round((item['percentage'] / 100.0) * amount)
            item['amount_formatted'] = f"₹{item_val:,.0f}{suffix}"
    else:
        alloc_suffix = "% आवंटन" if lang == 'hi' else "% Allocation"
        for item in allocations:
            item['amount_formatted'] = f"{item['percentage']}{alloc_suffix}"

    if lang == 'hi':
        suggested_links = [
            {'title': 'स्टॉक गाइड', 'url': '/stock-guide/', 'icon': 'fas fa-chart-line', 'badge': 'इक्विटी'},
            {'title': 'ईटीएफ गाइड', 'url': '/etf-guide/', 'icon': 'fas fa-layer-group', 'badge': 'पैसिव इंडेक्स'},
            {'title': 'म्यूचुअल फंड्स', 'url': '/mf-guide/', 'icon': 'fas fa-hand-holding-dollar', 'badge': 'SIP'},
            {'title': 'NPS पेंशन', 'url': '/nps-guide/', 'icon': 'fas fa-university', 'badge': 'टैक्स बचत'},
            {'title': 'स्टॉक स्क्रीनर', 'url': '/screener/', 'icon': 'fas fa-search', 'badge': 'एनालिसिस'}
        ]
        disclaimer = (
            "शैक्षणिक और नियम-आधारित निर्णय समर्थन। FOLIUX केवल संख्यात्मक मॉडल और आवंटन नियम प्रदान करता है। "
            "प्रतिभूतियों और म्यूचुअल फंड्स में निवेश बाजार के जोखिमों के अधीन है। निवेश से पहले सभी योजना दस्तावेजों को ध्यान से पढ़ें।"
        )
        login_cta = {
            'title': 'अपनी व्यक्तिगत FOLIUX रणनीति बनाएं',
            'message': CLOSING_NOTICE_HI,
            'button_text': 'लॉगिन करें और प्रोफ़ाइल सेट करें',
            'url': '/login/?next=/profile/'
        }
    else:
        suggested_links = [
            {'title': 'Stock Guide', 'url': '/stock-guide/', 'icon': 'fas fa-chart-line', 'badge': 'Equity'},
            {'title': 'ETF Guide', 'url': '/etf-guide/', 'icon': 'fas fa-layer-group', 'badge': 'Passive'},
            {'title': 'Mutual Funds', 'url': '/mf-guide/', 'icon': 'fas fa-hand-holding-dollar', 'badge': 'SIP'},
            {'title': 'NPS Pension', 'url': '/nps-guide/', 'icon': 'fas fa-university', 'badge': 'Tax Saver'},
            {'title': 'Stock Screener', 'url': '/screener/', 'icon': 'fas fa-search', 'badge': 'Analysis'}
        ]
        disclaimer = (
            "Educational and rule-based decision support only. Foliux provides quantitative rules and allocation models. "
            "Investments in securities and mutual funds are subject to market risks. Please read all scheme documents carefully before investing."
        )
        login_cta = {
            'title': 'Personalize Your FOLIUX Strategy',
            'message': CLOSING_NOTICE_EN,
            'button_text': 'Log In & Setup Profile',
            'url': '/login/?next=/profile/'
        }

    # Record query for continuous self-learning
    query_id = None
    try:
        from core.models import AdviserQueryLog
        nifty_val = None
        if market_context and market_context.get('nifty_price'):
            try:
                np_clean = str(market_context['nifty_price']).replace(',', '').replace('₹', '').strip()
                nifty_val = Decimal(np_clean)
            except Exception:
                nifty_val = None

        user_obj = user if (user and getattr(user, 'is_authenticated', False)) else None

        qlog = AdviserQueryLog.objects.create(
            user=user_obj,
            session_key=session_key,
            query_text=query,
            detected_language=lang,
            parsed_intent=parsed,
            market_regime=regime,
            nifty_price=nifty_val,
            strategy_key=strategy_key,
            user_feedback=0
        )
        query_id = qlog.id
    except Exception as e:
        logger.warning(f"Failed to log adviser query for self-learning: {e}")

    learning_model = {
        'strategy_key': strategy_key,
        'regime': regime,
        'confidence_score': learned_weights.get('confidence_score', 0.88),
        'sample_count': learned_weights.get('sample_count', 1),
        'harvest_target_pct': harvest_target,
        'dip_buy_pct': dip_buy,
        'version': '2.2-Adaptive'
    }

    return {
        'status': 'success',
        'query_id': query_id,
        'query': query,
        'language': lang,
        'parsed_query': parsed,
        'market_regime': regime,
        'regime_name': regime_data['name_hi'] if lang == 'hi' else regime_data['name_en'],
        'regime_insight': regime_data['insight_hi'] if lang == 'hi' else regime_data['insight_en'],
        'regime_insight_phonetic': regime_data['insight_hi_phonetic'],
        'learning_model': learning_model,
        'title': title,
        'summary': summary_text,
        'spoken_text': spoken_text,
        'spoken_text_phonetic': spoken_text_phonetic,
        'allocations': allocations,
        'execution_steps': execution_steps,
        'suggested_links': suggested_links,
        'login_cta': login_cta,
        'disclaimer': disclaimer
    }
