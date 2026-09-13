// Lightweight vanilla-JS i18n: no build step, matches this site's existing
// plain HTML/CSS/JS convention. Elements opt in via data-i18n="key" (sets
// textContent) or data-i18n-html="key" (sets innerHTML, for strings that
// need embedded markup like the accent <span> in the hero title).
const SUPPORTED_LANGS = ["ko", "en", "es", "zh", "ja"];
const LANG_LABELS = { ko: "한국어", en: "English", es: "Español", zh: "中文", ja: "日本語" };

const translations = {
  "brand.name": { ko: "수다메이트", en: "SooDaMate", es: "SooDaMate", zh: "SooDaMate", ja: "SooDaMate" },
  "nav.why": { ko: "차별점", en: "Why us", es: "Por qué nosotros", zh: "差异化优势", ja: "選ばれる理由" },
  "nav.features": { ko: "기능", en: "Features", es: "Funciones", zh: "功能", ja: "機能" },
  "nav.rule": { ko: "블라인드 채팅이란", en: "What's Blind Chat", es: "Qué es el chat a ciegas", zh: "什么是盲聊", ja: "ブラインドチャットとは" },
  "nav.safety": { ko: "안전", en: "Safety", es: "Seguridad", zh: "安全保障", ja: "安全性" },
  "nav.screens": { ko: "스크린샷", en: "Screenshots", es: "Capturas", zh: "截图", ja: "スクリーンショット" },
  "nav.download": { ko: "다운로드", en: "Download", es: "Descargar", zh: "下载", ja: "ダウンロード" },

  "hero.eyebrow": {
    ko: "🎭 인증된 회원만의 블라인드 채팅",
    en: "🎭 Blind chat, verified members only",
    es: "🎭 Chat a ciegas, solo miembros verificados",
    zh: "🎭 仅限认证会员的盲聊",
    ja: "🎭 認証済み会員限定のブラインドチャット",
  },
  "hero.title": {
    ko: '얼굴 공개는 천천히,<br /><span class="accent">대화는 지금 바로</span>',
    en: 'Reveal your face later.<br /><span class="accent">Start talking now</span>',
    es: 'Muestra tu cara más tarde.<br /><span class="accent">Empieza a hablar ya</span>',
    zh: '容貌稍后揭晓，<br /><span class="accent">对话现在开始</span>',
    ja: '顔を明かすのはあとで。<br /><span class="accent">会話は今すぐ始めよう</span>',
  },
  "hero.subtitle": {
    ko: "관심사가 통하는 인증된 회원과 먼저 대화부터 시작하세요. 이름과 사진은 서로 동의할 때만 공개돼요. 흔한 랜덤 채팅이 아닌, 진짜 인연을 위한 블라인드 매칭입니다.",
    en: "Start talking with verified members who share your interests. Names and photos are revealed only when you both agree. Not cheap random chat — real blind matching for real connection.",
    es: "Empieza a hablar con miembros verificados que comparten tus intereses. Los nombres y fotos solo se revelan cuando ambos lo acepten. No es un chat aleatorio cualquiera: es un emparejamiento a ciegas real para conexiones reales.",
    zh: "先和兴趣相投、通过认证的会员聊起来。姓名和照片只有双方都同意才会公开。这不是廉价的随机聊天，而是为真实缘分设计的盲配对。",
    ja: "興味が合う認証済み会員と、まず会話から始めよう。名前と写真はお互いが同意したときだけ公開されます。安っぽいランダムチャットではなく、本当の出会いのためのブラインドマッチングです。",
  },
  "hero.storeSoon": { ko: "출시 예정", en: "Coming soon", es: "Próximamente", zh: "即将上线", ja: "近日公開" },
  "hero.trust1": { ko: "전화번호 인증을 마친 회원만", en: "Phone-verified members only", es: "Solo miembros con teléfono verificado", zh: "仅限已完成手机验证的会员", ja: "電話番号認証済みの会員のみ" },
  "hero.trust2": { ko: "매칭 전까지 이름·사진 비공개", en: "Name & photo hidden until matched", es: "Nombre y foto ocultos hasta el match", zh: "配对前姓名与照片保密", ja: "マッチするまで名前・写真は非公開" },
  "hero.trust3": { ko: "실시간 신고·차단", en: "Real-time report & block", es: "Reporte y bloqueo en tiempo real", zh: "实时举报与拉黑", ja: "リアルタイム通報・ブロック" },
  "hero.matchToast": { ko: "🎭 대화가 시작됐어요!", en: "🎭 The conversation has started!", es: "🎭 ¡La conversación ha comenzado!", zh: "🎭 对话已经开始！", ja: "🎭 会話が始まりました！" },
  "hero.chatToast": { ko: "💬 실시간 채팅 연결됨", en: "💬 Live chat connected", es: "💬 Chat en vivo conectado", zh: "💬 实时聊天已连接", ja: "💬 リアルタイムチャット接続中" },
  "hero.cardDistance": { ko: "🎵 음악 카테고리", en: "🎵 Music category", es: "🎵 Categoría de música", zh: "🎵 音乐分类", ja: "🎵 音楽カテゴリー" },
  "hero.cardName": { ko: "S***, 27", en: "S***, 27", es: "S***, 27", zh: "S***, 27岁", ja: "S***, 27歳" },
  "hero.cardBio": {
    ko: "얼굴과 이름은 아직 비공개예요",
    en: "Name and photo are still hidden",
    es: "El nombre y la foto siguen ocultos",
    zh: "姓名和照片暂未公开",
    ja: "名前と写真はまだ非公開です",
  },
  "hero.chipMusic": { ko: "🎵 음악", en: "🎵 Music", es: "🎵 Música", zh: "🎵 音乐", ja: "🎵 音楽" },
  "hero.chipTravel": { ko: "🌍 여행", en: "🌍 Travel", es: "🌍 Viajes", zh: "🌍 旅行", ja: "🌍 旅行" },
  "hero.chipMovies": { ko: "🎬 영화", en: "🎬 Movies", es: "🎬 Películas", zh: "🎬 电影", ja: "🎬 映画" },

  "why.head.title": {
    ko: "다른 데이팅 앱과는 다릅니다",
    en: "What sets us apart",
    es: "Lo que nos hace diferentes",
    zh: "与其他交友软件不同",
    ja: "他のアプリとは違います",
  },
  "why.head.sub": {
    ko: "수다메이트만의 세 가지 차별점을 소개합니다.",
    en: "Three things you won't find on most other dating apps.",
    es: "Tres cosas que no encontrarás en la mayoría de otras apps de citas.",
    zh: "大多数其他交友软件都没有的三大特色。",
    ja: "他の多くのアプリにはない、3つの特徴です。",
  },
  "why.1.title": { ko: "신뢰 4종 세트", en: "Four-layer trust check", es: "Verificación de confianza en cuatro capas", zh: "四重信任保障", ja: "4つの信頼の証" },
  "why.1.body": {
    ko: "전화번호 인증, 사진 인증, 영상 프로필, 재직·학교 인증까지 — 네 가지 신뢰 장치를 동시에 갖춘 몇 안 되는 데이팅 앱이에요. 가짜 프로필 걱정은 이제 그만.",
    en: "Phone verification, photo verification, video profiles, and work/school verification — all four at once. One of the few dating apps with this much identity assurance built in.",
    es: "Verificación de teléfono, de foto, perfiles en video y verificación laboral/escolar, las cuatro a la vez. Una de las pocas apps de citas con tanta garantía de identidad.",
    zh: "手机号认证、照片认证、视频资料、职场/学校认证四重保障同时具备 —— 少数拥有如此完善身份保障的交友软件之一。",
    ja: "電話番号認証、写真認証、動画プロフィール、職場・学校認証。この4つを同時に備えたアプリはまだ多くありません。",
  },
  "why.2.title": {
    ko: "한국 + 다국어, 국경 없는 인연",
    en: "Korea, without the language barrier",
    es: "Corea, sin la barrera del idioma",
    zh: "在韩国，跨越语言的相遇",
    ja: "韓国で、言葉の壁を越えて",
  },
  "why.2.body": {
    ko: "5개 언어 지원과 언어교류 기능으로, 한국에 있는 외국인과 한국인이 자연스럽게 만날 수 있어요.",
    en: "With 5 languages and a language-exchange option, it's easy for Koreans and people living in Korea from anywhere to meet naturally.",
    es: "Con 5 idiomas y una opción de intercambio de idiomas, es fácil que coreanos y extranjeros en Corea se conozcan de forma natural.",
    zh: "支持5种语言，还有语言交流功能，让在韩外国人与韩国人能自然相识。",
    ja: "5言語対応と言語交換機能で、韓国在住の外国人と韓国人が自然に出会えます。",
  },
  "why.3.title": { ko: "필터는 무료로", en: "Filters, free", es: "Filtros, gratis", zh: "筛选功能，完全免费", ja: "フィルターは無料" },
  "why.3.body": {
    ko: "키·인종·언어·관심사 같은 필터를 프리미엄 결제 없이도 자유롭게 써보세요. 진짜 필요한 곳에만 돈을 쓰면 돼요.",
    en: "Height, ethnicity, languages, interests — filter by all of it without paying a cent. Spend on premium only where it actually matters.",
    es: "Altura, etnia, idiomas, intereses: fíltralo todo sin pagar nada. Paga premium solo donde realmente importa.",
    zh: "身高、种族、语言、兴趣等筛选条件，无需付费即可自由使用。把钱花在真正需要的地方。",
    ja: "身長・人種・言語・興味など、課金なしで自由にフィルターを使えます。本当に必要なところにだけ課金すればOK。",
  },

  "features.head.title": { ko: "왜 수다메이트일까요", en: "Why SooDaMate", es: "Por qué SooDaMate", zh: "为什么选择数搭伴侣", ja: "なぜ数多メイトなのか" },
  "features.head.sub": {
    ko: "인증된 회원과의 진짜 대화, 그리고 그 이후를 더 특별하게 만들어주는 기능들을 소개합니다.",
    en: "Real conversation with verified members — and the features that make everything after that even better.",
    es: "Conversaciones reales con miembros verificados, y las funciones que hacen que todo lo que viene después sea aún mejor.",
    zh: "与认证会员的真实对话，以及让这一切之后更加精彩的各种功能。",
    ja: "認証済み会員との本当の会話、そしてその先をもっと特別にしてくれる機能たちをご紹介します。",
  },
  "feature.2.title": { ko: "실시간 채팅", en: "Real-time chat", es: "Chat en tiempo real", zh: "实时聊天", ja: "リアルタイムチャット" },
  "feature.2.body": {
    ko: "매칭되는 순간 바로 대화를 시작할 수 있는 실시간 채팅으로, 어색한 정적 없이 이어집니다.",
    en: "The moment you match, jump straight into live conversation — no awkward silence in between.",
    es: "En cuanto haya match, pasa directo a una conversación en vivo, sin silencios incómodos.",
    zh: "配对瞬间即可开始实时对话，不留尴尬的沉默。",
    ja: "マッチした瞬間からリアルタイムで会話がスタート。気まずい沈黙はありません。",
  },
  "feature.4.title": { ko: "화상통화 매칭 확인", en: "Video call verification", es: "Verificación por videollamada", zh: "视频通话确认", ja: "ビデオ通話での本人確認" },
  "feature.4.body": {
    ko: "실제로 만나기 전, 화상통화로 서로를 먼저 확인할 수 있어 더 안심하고 다음 단계로 나아갈 수 있어요.",
    en: "Before meeting in person, see each other on a video call first — a safer, more confident step forward.",
    es: "Antes de quedar en persona, véanse primero por videollamada: un paso más seguro y con más confianza.",
    zh: "见面前先视频通话，看清彼此，让下一步更安心。",
    ja: "実際に会う前にビデオ通話でお互いを確認。より安心して次のステップに進めます。",
  },
  "feature.5.title": { ko: "재직·학교 인증 배지", en: "Work & school verification", es: "Verificación laboral y académica", zh: "职场与学校认证徽章", ja: "勤務先・学校認証バッジ" },
  "feature.5.body": {
    ko: "이메일 인증으로 재직 중인 회사나 학교를 인증하고, 프로필에 신뢰 배지를 표시할 수 있어요.",
    en: "Verify your workplace or school by email and show a trust badge right on your profile.",
    es: "Verifica tu empresa o universidad por correo y muestra una insignia de confianza en tu perfil.",
    zh: "通过邮箱认证在职公司或学校，在个人主页展示信任徽章。",
    ja: "メール認証で勤務先や学校を証明し、プロフィールに信頼バッジを表示できます。",
  },
  "feature.7.title": { ko: "블라인드 채팅", en: "Blind Chat", es: "Chat a ciegas", zh: "盲聊", ja: "ブラインドチャット" },
  "feature.7.body": {
    ko: "관심사가 통하는 검증된 회원과 먼저 대화부터 시작하세요. 이름과 사진은 서로 동의할 때만 공개돼요.",
    en: "Start with conversation, not a photo — chat with a verified member who shares your interests. Names and photos only go public once both sides agree.",
    es: "Empieza por la conversación, no por la foto — chatea con un miembro verificado que comparte tus intereses. Los nombres y fotos solo se revelan si ambos están de acuerdo.",
    zh: "先聊天，不看脸——与兴趣相投的认证会员开始匿名对话。只有双方都同意，姓名和照片才会公开。",
    ja: "写真より先に会話から — 趣味が合う認証済みメンバーとチャット。名前と写真はお互いが同意したときだけ公開されます。",
  },

  "how.head.title": { ko: "시작하는 방법", en: "How to get started", es: "Cómo empezar", zh: "如何开始", ja: "始め方" },
  "how.head.sub": {
    ko: "가입부터 첫 대화까지, 3단계면 충분합니다.",
    en: "From sign-up to your first conversation, it only takes 3 steps.",
    es: "Desde el registro hasta tu primera conversación, solo 3 pasos.",
    zh: "从注册到第一次对话，只需三步。",
    ja: "登録から最初の会話まで、たった3ステップ。",
  },
  "how.1.title": { ko: "가입 + 본인인증", en: "Sign up + verify", es: "Regístrate y verifícate", zh: "注册 + 实名认证", ja: "登録＋本人確認" },
  "how.1.body": {
    ko: "애플, 구글, 이메일 중 편한 방법으로 가입하고 전화번호 인증까지 간단히 끝내세요.",
    en: "Sign up with Apple, Google, or email — whichever's easiest — then verify your phone number in seconds.",
    es: "Regístrate con Apple, Google o correo, el que prefieras, y verifica tu teléfono en segundos.",
    zh: "选择Apple、谷歌或邮箱注册，几秒内完成手机号验证。",
    ja: "Apple、Google、メールの好きな方法で登録し、数秒で電話番号認証を済ませましょう。",
  },
  "how.2.title": { ko: "카테고리 선택", en: "Pick a category", es: "Elige una categoría", zh: "选择分类", ja: "カテゴリーを選ぶ" },
  "how.2.body": {
    ko: "관심 있는 주제를 고르면 비슷한 관심사를 가진 인증된 회원과 바로 연결돼요.",
    en: "Pick a topic you're into and get connected right away with a verified member who shares it.",
    es: "Elige un tema que te interese y conéctate al instante con un miembro verificado que lo comparte.",
    zh: "选一个感兴趣的话题，立刻与有相同兴趣的认证会员连接。",
    ja: "興味のあるトピックを選ぶと、同じ関心を持つ認証済み会員とすぐにつながれます。",
  },
  "how.3.title": { ko: "대화하다 동의하면 공개", en: "Chat, then reveal", es: "Chatea y luego revela", zh: "聊天后再公开", ja: "会話してから公開" },
  "how.3.body": {
    ko: "이름·사진 걱정 없이 편하게 대화하고, 둘 다 준비됐을 때 서로 동의하면 공개돼요.",
    en: "Chat freely with no name or photo attached — reveal them only once you both agree you're ready.",
    es: "Chatea libremente sin nombre ni foto de por medio; revélalos solo cuando ambos estén listos y de acuerdo.",
    zh: "无需顾虑姓名和照片，轻松聊天；当双方都准备好并同意后再互相公开。",
    ja: "名前も写真もない状態で気軽に会話し、お互い準備ができて同意したときだけ公開されます。",
  },

  "rule.badge": { ko: "🎭 이름도 사진도 없이 시작하는 대화", en: "🎭 No name, no photo — just talk", es: "🎭 Sin nombre, sin foto — solo hablar", zh: "🎭 没有姓名照片，先聊起来", ja: "🎭 名前も写真もなく、まず会話から" },
  "rule.title": {
    ko: "얼굴부터 보지 않아도<br />괜찮아요",
    en: "You don't have to see<br />a face first",
    es: "No tienes que ver<br />una cara primero",
    zh: "不用先看脸，<br />也没关系",
    ja: "最初に顔を見なくても<br />大丈夫",
  },
  "rule.p1": {
    ko: "블라인드 채팅은 이름도 사진도 없이 시작해요. 관심사가 통하는 인증된 회원과 먼저 대화를 나누면서, 외모가 아니라 대화가 잘 통하는지부터 확인할 수 있어요.",
    en: "Blind Chat starts with no name and no photo. Talk first with a verified member who shares your interests, and find out if the conversation clicks before looks ever enter the picture.",
    es: "El chat a ciegas empieza sin nombre ni foto. Habla primero con un miembro verificado que comparta tus intereses y descubre si conectan antes de ver una cara.",
    zh: "盲聊没有姓名也没有照片。先和兴趣相投的认证会员聊起来，确认聊得来之后再谈外貌。",
    ja: "ブラインドチャットは名前も写真もなしで始まります。興味が合う認証済み会員とまず話してみて、外見より先に会話の相性を確かめられます。",
  },
  "rule.p2": {
    ko: "대화하다 서로 준비가 됐다고 느끼면 언제든 공개를 요청할 수 있어요. 둘 다 동의해야만 이름과 사진이 공개됩니다.",
    en: "Once you both feel ready, either of you can request to reveal — names and photos only show once you both agree.",
    es: "Cuando ambos se sientan listos, cualquiera puede pedir revelar el perfil — el nombre y la foto solo se muestran si ambos están de acuerdo.",
    zh: "聊到双方都觉得准备好了，随时可以提出公开请求——只有双方都同意，姓名和照片才会公开。",
    ja: "お互い準備ができたと感じたら、いつでも公開をリクエストできます。名前と写真は双方が同意したときだけ公開されます。",
  },
  "rule.timeline1.title": { ko: "카테고리 매칭", en: "Category match", es: "Match por categoría", zh: "分类配对", ja: "カテゴリーマッチ" },
  "rule.timeline1.body": {
    ko: "같은 관심사를 고른 인증된 회원과 연결돼요.",
    en: "You're connected with a verified member who picked the same category.",
    es: "Te conectamos con un miembro verificado que eligió la misma categoría.",
    zh: "与选择了相同分类的认证会员建立连接。",
    ja: "同じカテゴリーを選んだ認証済み会員とつながります。",
  },
  "rule.timeline2.title": { ko: "비공개 대화", en: "Private conversation", es: "Conversación privada", zh: "匿名对话", ja: "非公開の会話" },
  "rule.timeline2.body": {
    ko: "이름과 사진 없이 편하게 대화를 나눠요.",
    en: "Chat comfortably with no name or photo attached.",
    es: "Chatea cómodamente sin nombre ni foto de por medio.",
    zh: "在没有姓名和照片的情况下轻松聊天。",
    ja: "名前も写真もない状態で気軽に会話できます。",
  },
  "rule.timeline3.title": { ko: "동의하면 공개", en: "Reveal, once you agree", es: "Revela, cuando ambos acepten", zh: "同意后公开", ja: "同意したら公開" },
  "rule.timeline3.body": {
    ko: "둘 다 원하면 그때 서로의 이름과 사진이 공개돼요.",
    en: "When you both want to, that's when names and photos are revealed to each other.",
    es: "Cuando ambos lo deseen, ese es el momento en que se revelan los nombres y las fotos.",
    zh: "只有双方都愿意时，才会互相公开姓名和照片。",
    ja: "お互いが望んだときに、初めて名前と写真がお互いに公開されます。",
  },

  "safety.1.title": { ko: "손쉬운 차단·신고", en: "Easy block & report", es: "Bloqueo y reporte fáciles", zh: "轻松拉黑与举报", ja: "簡単ブロック・通報" },
  "safety.1.body": {
    ko: "불편한 상대는 대화방에서 바로 차단하거나 신고할 수 있어요.",
    en: "Block or report anyone right from the chat, any time it feels wrong.",
    es: "Bloquea o reporta a cualquiera directamente desde el chat, cuando lo necesites.",
    zh: "在聊天界面即可直接拉黑或举报不合适的对象。",
    ja: "不快な相手はチャット画面からすぐにブロック・通報できます。",
  },
  "safety.2.title": { ko: "재직·학교 인증", en: "Work & school verification", es: "Verificación laboral y académica", zh: "职场与学校认证", ja: "勤務先・学校認証" },
  "safety.2.body": {
    ko: "이메일 인증을 거친 회원에게는 신뢰 배지가 표시돼요.",
    en: "Members who verify by email get a trust badge on their profile.",
    es: "Los miembros verificados por correo obtienen una insignia de confianza.",
    zh: "通过邮箱认证的会员将获得信任徽章展示。",
    ja: "メール認証を完了した会員には信頼バッジが表示されます。",
  },
  "safety.3.title": { ko: "화상통화로 먼저 확인", en: "Verify by video call first", es: "Verifica primero por videollamada", zh: "先视频通话确认", ja: "まずビデオ通話で確認" },
  "safety.3.body": {
    ko: "실제로 만나기 전에 화상통화로 서로를 확인할 수 있어요.",
    en: "See each other on a video call before ever meeting in person.",
    es: "Véanse por videollamada antes de encontrarse en persona.",
    zh: "见面前可先通过视频通话确认彼此。",
    ja: "実際に会う前にビデオ通話でお互いを確認できます。",
  },
  "safety.4.title": { ko: "만 18세 이상만 이용", en: "18+ only", es: "Solo mayores de 18 años", zh: "仅限18岁以上使用", ja: "18歳以上のみ利用可能" },
  "safety.4.body": {
    ko: "모든 회원은 가입 시 생년월일 확인을 거쳐요.",
    en: "Every member's birth date is checked at sign-up.",
    es: "Se verifica la fecha de nacimiento de cada miembro al registrarse.",
    zh: "所有会员注册时均需核实出生日期。",
    ja: "すべての会員は登録時に生年月日の確認を行います。",
  },
  "safety.card.title": { ko: "안전이 먼저입니다", en: "Safety comes first", es: "La seguridad es lo primero", zh: "安全第一", ja: "安全を第一に" },
  "safety.card.body": {
    ko: "진짜 인연은 신뢰에서 시작돼요. 수다메이트는 안전한 만남을 위한 장치를 계속 더해가고 있습니다.",
    en: "Real connection starts with trust. We keep adding new ways to make meeting people safer.",
    es: "La conexión real empieza con confianza. Seguimos sumando formas de hacer más segura cada conexión.",
    zh: "真正的缘分始于信任。数搭伴侣会持续增加更多安全保障功能。",
    ja: "本当の縁は信頼から始まります。数多メイトは安全な出会いのための仕組みを増やし続けています。",
  },

  "screens.head.title": { ko: "미리보기", en: "Sneak peek", es: "Vista previa", zh: "抢先预览", ja: "プレビュー" },
  "screens.head.sub": {
    ko: "실제 앱 스크린샷은 출시 후 이 자리에 업데이트됩니다.",
    en: "Real app screenshots will replace these once we launch.",
    es: "Las capturas reales de la app reemplazarán estas al lanzar.",
    zh: "正式上线后，这里将替换为真实应用截图。",
    ja: "実際のアプリのスクリーンショットはリリース後にここに掲載されます。",
  },
  "screens.discover": { ko: "카테고리 선택<br />블라인드 채팅 시작", en: "Pick a category<br />Start Blind Chat", es: "Elige categoría<br />Empieza el chat a ciegas", zh: "选择分类<br />开始盲聊", ja: "カテゴリーを選ぶ<br />ブラインドチャット開始" },
  "screens.match": { ko: "🎭 비공개 대화 중", en: "🎭 Chatting, still private", es: "🎭 Chateando, aún en privado", zh: "🎭 匿名对话中", ja: "🎭 非公開で会話中" },
  "screens.chat": { ko: "💛 서로 공개했어요!", en: "💛 You revealed each other!", es: "💛 ¡Se revelaron mutuamente!", zh: "💛 双方已互相公开！", ja: "💛 お互いに公開しました！" },

  "cta.title": { ko: "지금 바로 시작하세요", en: "Get started today", es: "Empieza hoy mismo", zh: "现在就开始吧", ja: "今すぐ始めよう" },
  "cta.body": {
    ko: "수다메이트는 곧 App Store와 Google Play에 출시됩니다.",
    en: "SooDaMate is launching soon on the App Store and Google Play.",
    es: "SooDaMate llega pronto a App Store y Google Play.",
    zh: "数搭伴侣即将登陆App Store和Google Play。",
    ja: "数多メイトはまもなくApp StoreとGoogle Playで公開予定です。",
  },

  "footer.rights": { ko: "© 2026 수다리스트. All rights reserved.", en: "© 2026 SooDaList. All rights reserved.", es: "© 2026 SooDaList. Todos los derechos reservados.", zh: "© 2026 SooDaList 保留所有权利。", ja: "© 2026 SooDaList. All rights reserved." },
  "footer.privacy": { ko: "개인정보처리방침", en: "Privacy Policy", es: "Política de privacidad", zh: "隐私政策", ja: "プライバシーポリシー" },
  "footer.terms": { ko: "이용약관", en: "Terms of Use", es: "Términos de uso", zh: "使用条款", ja: "利用規約" },
  "footer.deleteAccount": { ko: "계정 삭제", en: "Delete Account", es: "Eliminar cuenta", zh: "删除账户", ja: "アカウント削除" },

  "legal.back": { ko: "← 홈으로", en: "← Home", es: "← Inicio", zh: "← 返回首页", ja: "← ホームへ" },
  "legal.updated": { ko: "최종 수정일: 2026년 9월 4일", en: "Last updated: September 4, 2026", es: "Última actualización: 4 de septiembre de 2026", zh: "最后更新：2026年9月4日", ja: "最終更新日：2026年9月4日" },

  "privacy.title": { ko: "개인정보처리방침", en: "Privacy Policy", es: "Política de privacidad", zh: "隐私政策", ja: "プライバシーポリシー" },
  "privacy.intro": {
    ko: '수다리스트("회사")는 수다메이트 앱("서비스")을 운영하며, 이용자의 개인정보를 소중히 다룹니다. 본 방침은 서비스 이용 과정에서 수집하는 개인정보의 항목, 이용 목적, 보관 기간, 제3자 제공 및 이용자의 권리를 안내합니다.',
    en: 'SooDaList ("the Company") operates the SooDaMate app ("the Service") and takes your privacy seriously. This policy explains what personal data we collect, why, how long we keep it, who we share it with, and your rights.',
    es: 'SooDaList ("la Empresa") opera la app SooDaMate ("el Servicio") y se toma en serio tu privacidad. Esta política explica qué datos personales recopilamos, por qué, cuánto tiempo los conservamos, con quién los compartimos y cuáles son tus derechos.',
    zh: 'SooDaList（"公司"）运营数搭伴侣应用（"服务"），高度重视用户隐私。本政策说明我们收集哪些个人信息、收集目的、保存期限、第三方共享情况以及用户享有的权利。',
    ja: 'SooDaList（以下「当社」）は数多メイトアプリ（以下「本サービス」）を運営しており、利用者の個人情報を大切に取り扱います。本方針では、収集する個人情報の項目、利用目的、保管期間、第三者提供、および利用者の権利について説明します。',
  },
  "privacy.h1": { ko: "1. 수집하는 개인정보 항목", en: "1. Personal Data We Collect", es: "1. Datos personales que recopilamos", zh: "1. 我们收集的个人信息", ja: "1. 収集する個人情報の項目" },
  "privacy.s1.li1": {
    ko: "<strong>계정 정보</strong> — 이메일 주소, 비밀번호(해시 저장), 또는 구글/애플 소셜 로그인 시 제공되는 식별자·이메일",
    en: "<strong>Account info</strong> — email address, password (stored hashed), or the identifier/email provided by Google/Apple social login",
    es: "<strong>Datos de cuenta</strong> — correo electrónico, contraseña (almacenada como hash), o el identificador/correo proporcionado por el inicio de sesión social de Google/Apple",
    zh: "<strong>账户信息</strong> — 电子邮箱、密码（哈希存储），或谷歌/Apple社交登录提供的标识符和邮箱",
    ja: "<strong>アカウント情報</strong> — メールアドレス、パスワード（ハッシュ化して保存）、またはGoogle/Appleのソーシャルログイン時に提供される識別子・メールアドレス",
  },
  "privacy.s1.li2": {
    ko: "<strong>프로필 정보</strong> — 닉네임, 생년월일(만 나이 계산용), 성별, 관심 성별, 자기소개, 프로필 사진",
    en: "<strong>Profile info</strong> — display name, birth date (used to calculate age), gender, gender preference, bio, profile photos",
    es: "<strong>Datos de perfil</strong> — nombre visible, fecha de nacimiento (para calcular la edad), género, preferencia de género, biografía, fotos de perfil",
    zh: "<strong>个人主页信息</strong> — 昵称、出生日期（用于计算年龄）、性别、关注性别、个人简介、头像照片",
    ja: "<strong>プロフィール情報</strong> — ニックネーム、生年月日（年齢計算用）、性別、関心のある性別、自己紹介、プロフィール写真",
  },
  "privacy.s1.li3": {
    ko: "<strong>위치 정보</strong> — 이용자가 직접 입력하거나 기기에서 제공에 동의한 경우의 대략적 위치(위도/경도) — 주변 추천 거리 계산 목적으로만 사용",
    en: "<strong>Location</strong> — an approximate location (latitude/longitude) you enter or your device shares with consent — used only to calculate distance for nearby recommendations",
    es: "<strong>Ubicación</strong> — una ubicación aproximada (latitud/longitud) que ingresas o que tu dispositivo comparte con tu consentimiento, usada solo para calcular la distancia en recomendaciones cercanas",
    zh: "<strong>位置信息</strong> — 用户自行输入或经设备同意提供的大致位置（经纬度）— 仅用于计算附近推荐的距离",
    ja: "<strong>位置情報</strong> — 利用者が入力するか、端末が同意の上で提供するおおよその位置情報（緯度・経度）— 近隣のおすすめ距離計算にのみ使用",
  },
  "privacy.s1.li4": {
    ko: "<strong>활동 정보</strong> — 좋아요/패스/슈퍼좋아요 기록, 매칭 내역, 채팅 메시지 내용 및 전송 시각",
    en: "<strong>Activity</strong> — Like/Pass/Super Like records, match history, chat message content and timestamps",
    es: "<strong>Actividad</strong> — registros de Me gusta/Pasar/Super Like, historial de matches, contenido y horas de los mensajes de chat",
    zh: "<strong>活动信息</strong> — 喜欢/跳过/超级喜欢记录、配对历史、聊天消息内容及发送时间",
    ja: "<strong>アクティビティ情報</strong> — いいね・パス・スーパーいいねの記録、マッチ履歴、チャットメッセージの内容と送信時刻",
  },
  "privacy.s1.li5": {
    ko: "<strong>기기 정보</strong> — 푸시 알림 발송을 위한 기기 토큰, 운영체제(iOS/Android) 구분",
    en: "<strong>Device info</strong> — device token for push notifications, OS (iOS/Android)",
    es: "<strong>Datos del dispositivo</strong> — token del dispositivo para notificaciones push, sistema operativo (iOS/Android)",
    zh: "<strong>设备信息</strong> — 用于推送通知的设备令牌、操作系统（iOS/Android）区分",
    ja: "<strong>デバイス情報</strong> — プッシュ通知送信のためのデバイストークン、OS（iOS/Android）の区分",
  },
  "privacy.s1.li6": {
    ko: "<strong>신고/차단 정보</strong> — 다른 이용자를 신고하거나 차단한 기록 (서비스 안전 목적)",
    en: "<strong>Report/block records</strong> — records of users you've reported or blocked (for service safety)",
    es: "<strong>Registros de reportes/bloqueos</strong> — registros de usuarios que has reportado o bloqueado (para la seguridad del servicio)",
    zh: "<strong>举报/拉黑信息</strong> — 举报或拉黑其他用户的记录（用于服务安全目的）",
    ja: "<strong>通報・ブロック情報</strong> — 他の利用者を通報またはブロックした記録（サービス安全のため）",
  },
  "privacy.h2": { ko: "2. 개인정보 이용 목적", en: "2. Why We Use Your Data", es: "2. Para qué usamos tus datos", zh: "2. 个人信息使用目的", ja: "2. 個人情報の利用目的" },
  "privacy.s2.li1": { ko: "회원 가입 및 본인 확인, 로그인 인증", en: "Account sign-up, identity confirmation, and login authentication", es: "Registro de cuenta, confirmación de identidad y autenticación de inicio de sesión", zh: "会员注册、身份确认、登录认证", ja: "会員登録、本人確認、ログイン認証" },
  "privacy.s2.li2": { ko: "매칭 상대 추천 및 매칭 서비스 제공", en: "Recommending matches and providing the matching service", es: "Recomendar posibles matches y ofrecer el servicio de emparejamiento", zh: "推荐匹配对象及提供配对服务", ja: "マッチング相手の推薦およびマッチングサービスの提供" },
  "privacy.s2.li3": { ko: "실시간 채팅 및 매칭/메시지 알림(푸시) 발송", en: "Real-time chat and sending match/message push notifications", es: "Chat en tiempo real y envío de notificaciones push de matches/mensajes", zh: "实时聊天及配对/消息推送通知发送", ja: "リアルタイムチャット、マッチ・メッセージのプッシュ通知送信" },
  "privacy.s2.li4": { ko: "부정 이용 방지, 신고·차단 처리 및 서비스 안전 관리", en: "Preventing fraud/abuse and handling reports, blocks, and service safety", es: "Prevención de fraude/abuso y gestión de reportes, bloqueos y seguridad del servicio", zh: "防止不当使用、处理举报与拉黑及服务安全管理", ja: "不正利用防止、通報・ブロック対応、サービスの安全管理" },
  "privacy.s2.li5": { ko: "서비스 개선 및 통계 분석 (개인 식별이 불가능한 형태로 가공)", en: "Improving the service and statistical analysis (processed so individuals can't be identified)", es: "Mejorar el servicio y análisis estadístico (procesado de forma que no se pueda identificar a personas)", zh: "服务改进与统计分析（以无法识别个人身份的形式处理）", ja: "サービス改善および統計分析（個人を特定できない形に加工）" },
  "privacy.h3": { ko: "3. 개인정보 보관 및 파기", en: "3. Data Retention and Deletion", es: "3. Conservación y eliminación de datos", zh: "3. 个人信息的保存与销毁", ja: "3. 個人情報の保管および破棄" },
  "privacy.s3": {
    ko: '이용자가 앱 내 "설정 &gt; 계정 삭제"를 통해 탈퇴하면, 계정 및 이에 연결된 프로필, 사진, 매칭, 채팅 기록은 지체 없이 삭제됩니다. 관계 법령에 따라 일정 기간 보관이 필요한 정보(예: 부정 이용 기록)는 해당 법령이 정한 기간 동안만 별도 보관 후 파기합니다.',
    en: 'If you delete your account via "Settings &gt; Delete Account" in the app, your account and all linked profile data, photos, matches, and chat history are deleted without delay. Information legally required to be retained (e.g. fraud/abuse records) is kept separately only for the period the law requires, then destroyed.',
    es: 'Si eliminas tu cuenta desde "Configuración &gt; Eliminar cuenta" en la app, tu cuenta y todos los datos de perfil, fotos, matches e historial de chat vinculados se eliminan sin demora. La información que la ley exige conservar (p. ej. registros de fraude/abuso) se guarda por separado solo durante el período legal requerido, y luego se destruye.',
    zh: '如用户通过应用内"设置 &gt; 删除账户"注销，账户及关联的个人主页、照片、配对、聊天记录将被立即删除。依法需保留的信息（如不当使用记录）将仅在法定期限内单独保存，期满后销毁。',
    ja: 'アプリ内の「設定 &gt; アカウント削除」から退会すると、アカウントおよび関連するプロフィール、写真、マッチ、チャット履歴は遅滞なく削除されます。法令により一定期間の保管が必要な情報（例：不正利用記録）は、当該法令が定める期間のみ別途保管した後に破棄します。',
  },
  "privacy.h4": { ko: "4. 제3자 제공 및 처리 위탁", en: "4. Third-Party Sharing and Processing", es: "4. Compartir con terceros y procesamiento", zh: "4. 第三方提供及处理委托", ja: "4. 第三者提供および処理委託" },
  "privacy.s4.intro": {
    ko: "서비스 운영을 위해 아래 외부 서비스를 이용하며, 각 서비스의 자체 개인정보처리방침이 함께 적용될 수 있습니다.",
    en: "We use the external services below to operate the app; each one's own privacy policy may also apply.",
    es: "Usamos los siguientes servicios externos para operar la app; también puede aplicarse la política de privacidad propia de cada uno.",
    zh: "为运营本服务，我们使用以下外部服务，各服务自身的隐私政策也可能同时适用。",
    ja: "サービス運営のため以下の外部サービスを利用しており、各サービス独自のプライバシーポリシーが併せて適用される場合があります。",
  },
  "privacy.s4.li1": { ko: "<strong>Google / Apple</strong> — 소셜 로그인 인증", en: "<strong>Google / Apple</strong> — social login authentication", es: "<strong>Google / Apple</strong> — autenticación de inicio de sesión social", zh: "<strong>谷歌 / Apple</strong> — 社交登录认证", ja: "<strong>Google / Apple</strong> — ソーシャルログイン認証" },
  "privacy.s4.li2": { ko: "<strong>Google Cloud Platform</strong> — 서버 인프라, 데이터베이스, 프로필 사진 저장(Cloud Storage)", en: "<strong>Google Cloud Platform</strong> — server infrastructure, database, profile photo storage (Cloud Storage)", es: "<strong>Google Cloud Platform</strong> — infraestructura de servidor, base de datos, almacenamiento de fotos de perfil (Cloud Storage)", zh: "<strong>谷歌云平台</strong> — 服务器基础设施、数据库、头像存储（Cloud Storage）", ja: "<strong>Google Cloud Platform</strong> — サーバーインフラ、データベース、プロフィール写真の保存（Cloud Storage）" },
  "privacy.s4.li3": { ko: "<strong>Firebase Cloud Messaging</strong> — 매칭/메시지 푸시 알림 발송", en: "<strong>Firebase Cloud Messaging</strong> — sending match/message push notifications", es: "<strong>Firebase Cloud Messaging</strong> — envío de notificaciones push de matches/mensajes", zh: "<strong>Firebase Cloud Messaging</strong> — 配对/消息推送通知发送", ja: "<strong>Firebase Cloud Messaging</strong> — マッチ・メッセージのプッシュ通知送信" },
  "privacy.s4.li4": { ko: "<strong>Google AdMob</strong> — 앱 내 광고 게재 (광고 식별자 기반 맞춤 광고 포함 가능)", en: "<strong>Google AdMob</strong> — in-app advertising (may include ad-ID-based personalized ads)", es: "<strong>Google AdMob</strong> — publicidad dentro de la app (puede incluir anuncios personalizados basados en el ID de publicidad)", zh: "<strong>谷歌 AdMob</strong> — 应用内广告投放（可能包含基于广告标识符的个性化广告）", ja: "<strong>Google AdMob</strong> — アプリ内広告配信（広告識別子に基づくパーソナライズ広告を含む場合があります）" },
  "privacy.h5": { ko: "5. 이용자의 권리", en: "5. Your Rights", es: "5. Tus derechos", zh: "5. 用户的权利", ja: "5. 利用者の権利" },
  "privacy.s5": {
    ko: "이용자는 언제든지 앱 내에서 본인의 프로필 정보를 열람·수정할 수 있으며, 계정 삭제를 통해 개인정보 처리 정지 및 삭제를 요청할 수 있습니다. 만 18세 미만은 서비스를 이용할 수 없습니다.",
    en: "You can view and edit your profile information in the app at any time, and can request that we stop processing and delete your personal data by deleting your account. Anyone under 18 may not use the Service.",
    es: "Puedes ver y editar la información de tu perfil en la app en cualquier momento, y puedes solicitar que dejemos de procesar y eliminemos tus datos personales eliminando tu cuenta. Los menores de 18 años no pueden usar el Servicio.",
    zh: "用户可随时在应用内查看、修改本人的个人主页信息，并可通过删除账户要求停止处理及删除个人信息。未满18岁者不得使用本服务。",
    ja: "利用者はいつでもアプリ内で自身のプロフィール情報を閲覧・修正でき、アカウント削除により個人情報の処理停止および削除を要求できます。満18歳未満の方は本サービスをご利用いただけません。",
  },
  "privacy.h6": { ko: "6. 문의처", en: "6. Contact", es: "6. Contacto", zh: "6. 联系方式", ja: "6. お問い合わせ" },
  "privacy.s6": {
    ko: '개인정보 관련 문의: <a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a>',
    en: 'Privacy inquiries: <a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a>',
    es: 'Consultas sobre privacidad: <a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a>',
    zh: '隐私相关咨询：<a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a>',
    ja: '個人情報に関するお問い合わせ：<a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a>',
  },

  "deleteAccount.title": { ko: "계정 삭제 안내", en: "Delete Your Account", es: "Eliminar tu cuenta", zh: "删除账户说明", ja: "アカウント削除について" },
  "deleteAccount.intro": {
    ko: "수다메이트(SooDaMate) 앱을 운영하는 SooDaList는 이용자가 언제든지 본인의 계정과 데이터를 삭제할 수 있도록 안내합니다.",
    en: "SooDaList, which operates the SooDaMate app, lets you delete your account and data at any time.",
    es: "SooDaList, que opera la app SooDaMate, te permite eliminar tu cuenta y tus datos en cualquier momento.",
    zh: "运营数搭伴侣（SooDaMate）应用的SooDaList，让你可以随时删除自己的账户和数据。",
    ja: "SooDaMateアプリを運営するSooDaListは、いつでもアカウントとデータを削除できるようご案内します。",
  },
  "deleteAccount.h1": { ko: "1. 앱에서 직접 삭제하기", en: "1. Delete in the app", es: "1. Eliminar desde la app", zh: "1. 在应用内删除", ja: "1. アプリ内で削除する" },
  "deleteAccount.step1": {
    ko: "수다메이트 앱을 열고 로그인합니다.",
    en: "Open the SooDaMate app and log in.",
    es: "Abre la app SooDaMate e inicia sesión.",
    zh: "打开数搭伴侣应用并登录。",
    ja: "SooDaMateアプリを開いてログインします。",
  },
  "deleteAccount.step2": {
    ko: "프로필 탭 > 설정으로 이동합니다.",
    en: "Go to the Profile tab > Settings.",
    es: "Ve a la pestaña Perfil > Ajustes.",
    zh: "进入“我的”标签 > 设置。",
    ja: "プロフィールタブ > 設定に進みます。",
  },
  "deleteAccount.step3": {
    ko: '"계정 삭제"를 선택하고 안내에 따라 확인합니다.',
    en: 'Select "Delete account" and confirm.',
    es: 'Selecciona "Eliminar cuenta" y confirma.',
    zh: "选择“删除账户”并按提示确认。",
    ja: "「アカウント削除」を選択し、案内に従って確定します。",
  },
  "deleteAccount.h2": { ko: "2. 앱을 사용할 수 없는 경우", en: "2. If you can't access the app", es: "2. Si no puedes acceder a la app", zh: "2. 无法使用应用时", ja: "2. アプリが使えない場合" },
  "deleteAccount.noAppBody": {
    ko: '로그인할 수 없거나 앱을 삭제하셨다면, <a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a>으로 가입 시 사용한 이메일 주소와 함께 계정 삭제를 요청해 주세요. 본인 확인 후 처리해 드립니다.',
    en: 'If you can\'t log in or no longer have the app installed, email <a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a> with the address you signed up with to request deletion. We\'ll verify your identity and process it.',
    es: 'Si no puedes iniciar sesión o ya no tienes la app instalada, escribe a <a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a> con el correo con el que te registraste para solicitar la eliminación. Verificaremos tu identidad y lo procesaremos.',
    zh: '如果无法登录或已卸载应用，请发送邮件至 <a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a>，附上注册时使用的邮箱地址以申请删除。我们核实身份后会为你处理。',
    ja: 'ログインできない、またはアプリをすでに削除した場合は、<a href="mailto:privacy@soodamate.com">privacy@soodamate.com</a> に登録時のメールアドレスを添えて削除をご依頼ください。本人確認の上、対応いたします。',
  },
  "deleteAccount.h3": { ko: "3. 삭제되는 데이터", en: "3. What gets deleted", es: "3. Qué se elimina", zh: "3. 会被删除的数据", ja: "3. 削除されるデータ" },
  "deleteAccount.dataIntro": {
    ko: "계정을 삭제하면 아래 데이터가 지체 없이 영구적으로 삭제됩니다:",
    en: "Deleting your account permanently removes the following data right away:",
    es: "Al eliminar tu cuenta, se elimina permanentemente y de inmediato lo siguiente:",
    zh: "删除账户后，以下数据将立即被永久删除：",
    ja: "アカウントを削除すると、以下のデータが直ちに完全に削除されます：",
  },
  "deleteAccount.data1": {
    ko: "프로필 정보(닉네임, 생년월일, 성별, 자기소개, 위치)",
    en: "Profile info (name, birth date, gender, bio, location)",
    es: "Información de perfil (nombre, fecha de nacimiento, género, biografía, ubicación)",
    zh: "个人资料（昵称、出生日期、性别、简介、位置）",
    ja: "プロフィール情報（ニックネーム、生年月日、性別、自己紹介、位置情報）",
  },
  "deleteAccount.data2": { ko: "프로필 사진", en: "Profile photos", es: "Fotos de perfil", zh: "个人照片", ja: "プロフィール写真" },
  "deleteAccount.data3": {
    ko: "매칭 및 좋아요/패스/슈퍼좋아요 기록",
    en: "Matches and Like/Pass/Super Like history",
    es: "Matches e historial de Me gusta/Pasar/Super Like",
    zh: "配对及喜欢/跳过/超级喜欢记录",
    ja: "マッチおよびいいね・パス・スーパーいいねの履歴",
  },
  "deleteAccount.data4": { ko: "채팅 메시지 전체", en: "All chat messages", es: "Todos los mensajes de chat", zh: "全部聊天消息", ja: "すべてのチャットメッセージ" },
  "deleteAccount.data5": { ko: "신고/차단 기록", en: "Report/block history", es: "Historial de reportes/bloqueos", zh: "举报/拉黑记录", ja: "通報・ブロック履歴" },
  "deleteAccount.retention": {
    ko: "별도의 보관 기간 없이 즉시 삭제되며, 관계 법령상 보관 의무가 있는 정보만 해당 법령이 정한 기간 동안 예외적으로 보관됩니다.",
    en: "Deletion is immediate with no retention period, except for information we're legally required to retain, which is kept only as long as the law requires.",
    es: "La eliminación es inmediata y sin período de retención, salvo la información que estemos legalmente obligados a conservar, que se guarda solo durante el tiempo que exija la ley.",
    zh: "数据将立即删除，不设保留期限，唯有法律要求保留的信息，仅在法律规定的期限内例外保留。",
    ja: "保存期間を設けず直ちに削除されますが、法令上保管義務のある情報のみ、法令が定める期間に限り例外的に保管されます。",
  },

  "terms.title": { ko: "이용약관", en: "Terms of Use", es: "Términos de uso", zh: "使用条款", ja: "利用規約" },
  "terms.a1.title": { ko: "제1조 (목적)", en: "Article 1 (Purpose)", es: "Artículo 1 (Objeto)", zh: "第1条（目的）", ja: "第1条（目的）" },
  "terms.a1.body": {
    ko: '본 약관은 수다리스트("회사")가 제공하는 수다메이트 앱 서비스("서비스")의 이용과 관련하여 회사와 이용자 간의 권리, 의무 및 책임사항을 정함을 목적으로 합니다.',
    en: 'These Terms set out the rights, obligations, and responsibilities between SooDaList ("the Company") and users regarding the use of the SooDaMate app service ("the Service").',
    es: 'Estos Términos establecen los derechos, obligaciones y responsabilidades entre SooDaList ("la Empresa") y los usuarios en relación con el uso del servicio de la app SooDaMate ("el Servicio").',
    zh: '本条款旨在规定SooDaList（"公司"）提供的数搭伴侣应用服务（"服务"）使用过程中公司与用户之间的权利、义务及责任事项。',
    ja: '本規約は、SooDaList（以下「当社」）が提供する数多メイトアプリサービス（以下「本サービス」）の利用に関し、当社と利用者間の権利、義務及び責任事項を定めることを目的とします。',
  },
  "terms.a2.title": { ko: "제2조 (이용 자격)", en: "Article 2 (Eligibility)", es: "Artículo 2 (Requisitos de uso)", zh: "第2条（使用资格）", ja: "第2条（利用資格）" },
  "terms.a2.body": {
    ko: "서비스는 만 18세 이상만 이용할 수 있습니다. 가입 시 제공한 생년월일이 사실과 다른 경우 회사는 이용을 제한할 수 있습니다.",
    en: "The Service is available only to those 18 or older. If the birth date provided at sign-up is false, the Company may restrict use.",
    es: "El Servicio está disponible solo para mayores de 18 años. Si la fecha de nacimiento indicada en el registro es falsa, la Empresa puede restringir el uso.",
    zh: "本服务仅限满18岁人士使用。若注册时提供的出生日期不实，公司可限制其使用。",
    ja: "本サービスは満18歳以上のみご利用いただけます。登録時に提供した生年月日が事実と異なる場合、当社は利用を制限することがあります。",
  },
  "terms.a3.title": { ko: "제3조 (계정 및 보안)", en: "Article 3 (Account and Security)", es: "Artículo 3 (Cuenta y seguridad)", zh: "第3条（账户与安全）", ja: "第3条（アカウントおよびセキュリティ）" },
  "terms.a3.li1": { ko: "이용자는 본인의 계정 정보를 안전하게 관리할 책임이 있습니다.", en: "Users are responsible for keeping their account information secure.", es: "Los usuarios son responsables de mantener segura la información de su cuenta.", zh: "用户有责任妥善保管本人账户信息。", ja: "利用者は自身のアカウント情報を安全に管理する責任を負います。" },
  "terms.a3.li2": { ko: "이메일/비밀번호, 구글, 애플 중 하나 이상의 방법으로 가입할 수 있습니다.", en: "You may sign up using email/password, Google, or Apple, or more than one.", es: "Puedes registrarte usando correo/contraseña, Google o Apple, o más de uno.", zh: "可通过邮箱/密码、谷歌、Apple中的一种或多种方式注册。", ja: "メール/パスワード、Google、Appleのいずれか一つ以上の方法で登録できます。" },
  "terms.a3.li3": { ko: "타인의 정보를 도용하거나 허위 정보로 프로필을 작성하는 행위는 금지됩니다.", en: "Impersonating someone else or creating a profile with false information is prohibited.", es: "Está prohibido suplantar a otra persona o crear un perfil con información falsa.", zh: "禁止盗用他人信息或以虚假信息编写个人主页。", ja: "他人の情報を盗用したり、虚偽の情報でプロフィールを作成したりする行為は禁止です。" },
  "terms.a4.title": { ko: "제4조 (이용자의 의무 — Acceptable Use Policy)", en: "Article 4 (User Obligations — Acceptable Use Policy)", es: "Artículo 4 (Obligaciones del usuario — Política de Uso Aceptable)", zh: "第4条（用户义务 — Acceptable Use Policy）", ja: "第4条（利用者の義務 — Acceptable Use Policy）" },
  "terms.a4.intro": { ko: "이용자는 다음 행위를 해서는 안 됩니다.", en: "Users must not do the following:", es: "Los usuarios no deben hacer lo siguiente:", zh: "用户不得从事以下行为：", ja: "利用者は以下の行為をしてはなりません。" },
  "terms.a4.li1": { ko: "허위 프로필 작성 또는 타인을 사칭하는 행위", en: "Creating a false profile or impersonating another person", es: "Crear un perfil falso o suplantar a otra persona", zh: "编写虚假个人主页或冒充他人", ja: "虚偽のプロフィールを作成したり、他人になりすましたりする行為" },
  "terms.a4.li2": { ko: "다른 이용자에 대한 욕설, 희롱, 스토킹, 위협 등 부적절한 행위", en: "Abuse, harassment, stalking, threats, or other inappropriate conduct toward other users", es: "Insultos, acoso, acecho, amenazas u otra conducta inapropiada hacia otros usuarios", zh: "对其他用户辱骂、骚扰、跟踪、威胁等不当行为", ja: "他の利用者に対する暴言、嫌がらせ、ストーカー行為、脅迫等の不適切な行為" },
  "terms.a4.li3": { ko: "상업적 광고, 스팸, 사기성 메시지 전송", en: "Sending commercial advertising, spam, or fraudulent messages", es: "Envío de publicidad comercial, spam o mensajes fraudulentos", zh: "发送商业广告、垃圾信息或欺诈性消息", ja: "商業広告、スパム、詐欺的メッセージの送信" },
  "terms.a4.li4": { ko: "미성년자를 대상으로 하거나 미성년자가 이용하는 행위", en: "Targeting minors, or use of the Service by minors", es: "Dirigirse a menores de edad, o el uso del Servicio por menores", zh: "以未成年人为对象或未成年人使用本服务", ja: "未成年者を対象とする、または未成年者が利用する行為" },
  "terms.a4.li5": { ko: "서비스의 정상적인 운영을 방해하는 행위(자동화 도구 사용 등)", en: "Interfering with normal operation of the Service (e.g. using automated tools)", es: "Interferir con el funcionamiento normal del Servicio (p. ej. uso de herramientas automatizadas)", zh: "妨碍服务正常运营的行为（如使用自动化工具等）", ja: "本サービスの正常な運営を妨害する行為（自動化ツールの使用等）" },
  "terms.a4.li6": { ko: "인신매매, 성적 착취를 포함한 착취 행위, 또는 이를 조장·방조·권유하는 행위", en: "Human trafficking, exploitation (including sexual exploitation), or facilitating, promoting, or soliciting such conduct", es: "Trata de personas, explotación (incluida la explotación sexual), o facilitar, promover o solicitar dicha conducta", zh: "人口贩卖、剥削（包括性剥削），或协助、助长、招揽此类行为", ja: "人身売買、性的搾取を含む搾取行為、またはそれらを助長・幇助・勧誘する行為" },
  "terms.a4.li7": { ko: "아동을 성적으로 대상화하거나 아동 성적 학대·착취(아동 성 착취물 포함)와 관련된 일체의 콘텐츠 게시 또는 행위 — 발견 즉시 콘텐츠를 삭제하고 계정을 영구 정지하며 관계 당국에 신고합니다", en: "Sexualizing children, or any content or conduct related to child sexual abuse or exploitation (including child sexual abuse material) — upon discovery, the Company immediately removes the content, permanently suspends the account, and reports it to the relevant authorities", es: "Sexualizar a menores, o cualquier contenido o conducta relacionada con el abuso o la explotación sexual infantil (incluido el material de abuso sexual infantil) — al detectarlo, la Empresa elimina de inmediato el contenido, suspende permanentemente la cuenta y lo denuncia a las autoridades correspondientes", zh: "对儿童进行性化描绘，或任何与儿童性虐待、性剥削（包括儿童性虐待材料）相关的内容或行为 — 一经发现，公司将立即删除内容、永久停用账户并向相关部门举报", ja: "児童を性的に対象化する行為、または児童の性的虐待・搾取（児童性的虐待資料を含む）に関連するあらゆるコンテンツの投稿や行為 — 発見次第、当社は当該コンテンツを直ちに削除し、アカウントを永久停止のうえ関係当局へ通報します" },
  "terms.a4.li8": { ko: "성폭력을 조장, 묘사, 정당화하거나 이를 권유하는 행위", en: "Facilitating, depicting, condoning, or soliciting sexual violence", es: "Facilitar, representar, justificar o solicitar violencia sexual", zh: "助长、描绘、美化或招揽性暴力行为", ja: "性的暴力を助長、描写、正当化、または勧誘する行為" },
  "terms.a4.li9": { ko: "본인의 동의 없이 촬영되었거나 유포에 동의하지 않은 사진·영상 등 비동의 콘텐츠를 게시·유포하는 행위", en: "Posting or distributing non-consensual content, such as images or videos taken or shared without the subject's consent", es: "Publicar o distribuir contenido no consentido, como imágenes o videos tomados o compartidos sin el consentimiento del sujeto", zh: "发布或传播未经本人同意拍摄或分享的照片、视频等非自愿内容", ja: "本人の同意なく撮影または共有された写真・動画等、非同意コンテンツを投稿・拡散する行為" },
  "terms.a4.li10": { ko: "프로필 사진, 자기소개 등에 노골적인 성적 콘텐츠(나체, 성행위 묘사 등)를 게시하는 행위", en: "Posting sexually explicit content (nudity, depictions of sexual acts, etc.) in profile photos, bio, or elsewhere on the Service", es: "Publicar contenido sexualmente explícito (desnudez, representaciones de actos sexuales, etc.) en fotos de perfil, biografía u otras partes del Servicio", zh: "在个人资料照片、自我介绍等处发布露骨的性内容（裸露、性行为描绘等）", ja: "プロフィール写真や自己紹介等に露骨な性的コンテンツ（ヌード、性行為の描写等）を投稿する行為" },
  "terms.a4.li11": { ko: "로맨스 스캠 등 다른 이용자를 기망하여 금전적·재산상 이익을 편취하려는 사기 행위", en: "Scam activity intended to defraud other users of money or property, such as romance scams", es: "Actividad fraudulenta destinada a estafar a otros usuarios en dinero o bienes, como las estafas románticas", zh: "以婚恋交友诈骗等方式骗取其他用户钱财或财产的欺诈行为", ja: "ロマンス詐欺等、他の利用者を欺いて金銭・財産上の利益を騙し取ろうとする詐欺行為" },
  "terms.a4.li12": { ko: "관계 법령을 위반하는 일체의 불법 행위", en: "Any act that violates applicable law", es: "Cualquier acto que infrinja la ley aplicable", zh: "任何违反适用法律的行为", ja: "適用法令に違反する一切の行為" },
  "terms.a5.title": { ko: "제5조 (신고 및 제재)", en: "Article 5 (Reports and Sanctions)", es: "Artículo 5 (Reportes y sanciones)", zh: "第5条（举报与制裁）", ja: "第5条（通報および制裁）" },
  "terms.a5.body": {
    ko: "회사는 이용자 신고 또는 자체 모니터링을 통해 본 약관을 위반한 것으로 확인된 이용자에 대해 경고, 이용 제한, 계정 정지 등의 조치를 취할 수 있습니다. 차단 기능을 통해 이용자는 원치 않는 상대와의 매칭·메시지를 스스로 차단할 수 있습니다.",
    en: "The Company may warn, restrict, or suspend the account of a user found — via user reports or its own monitoring — to have violated these Terms. Using the block feature, users can block matching/messaging with anyone they don't want contact from.",
    es: "La Empresa puede advertir, restringir o suspender la cuenta de un usuario que, mediante reportes de usuarios o supervisión propia, se determine que ha violado estos Términos. Mediante la función de bloqueo, los usuarios pueden bloquear el emparejamiento/mensajería con quien no deseen contacto.",
    zh: "公司可通过用户举报或自行监控，对确认违反本条款的用户采取警告、限制使用、账户暂停等措施。用户可通过拉黑功能自行阻止与不希望联系的对象进行配对或消息往来。",
    ja: "当社は、利用者からの通報または自社モニタリングにより本規約に違反したことが確認された利用者に対し、警告、利用制限、アカウント停止等の措置を取ることがあります。利用者はブロック機能により、望まない相手とのマッチング・メッセージを自ら遮断できます。",
  },
  "terms.a6.title": { ko: "제6조 (서비스 제공 및 변경)", en: "Article 6 (Providing and Changing the Service)", es: "Artículo 6 (Prestación y modificación del Servicio)", zh: "第6条（服务的提供与变更）", ja: "第6条（サービスの提供および変更）" },
  "terms.a6.body": {
    ko: "회사는 서비스의 전부 또는 일부를 운영상, 기술상 필요에 따라 변경하거나 중단할 수 있으며, 중요한 변경 사항은 앱 또는 웹사이트를 통해 사전 공지합니다.",
    en: "The Company may change or discontinue all or part of the Service for operational or technical reasons, and will give advance notice of significant changes via the app or website.",
    es: "La Empresa puede modificar o discontinuar todo o parte del Servicio por razones operativas o técnicas, y notificará con anticipación los cambios significativos a través de la app o el sitio web.",
    zh: "公司可因运营或技术需要变更或中止服务的全部或部分内容，重大变更将通过应用或网站提前公告。",
    ja: "当社は運営上・技術上の必要に応じてサービスの全部または一部を変更または中断することがあり、重要な変更事項はアプリまたはウェブサイトを通じて事前に告知します。",
  },
  "terms.a7.title": { ko: "제7조 (계정 삭제)", en: "Article 7 (Account Deletion)", es: "Artículo 7 (Eliminación de cuenta)", zh: "第7条（账户删除）", ja: "第7条（アカウント削除）" },
  "terms.a7.body": {
    ko: '이용자는 앱 내 "설정 &gt; 계정 삭제"를 통해 언제든지 자유롭게 탈퇴할 수 있으며, 관련 개인정보 처리는 개인정보처리방침에 따릅니다.',
    en: 'Users may freely delete their account at any time via "Settings &gt; Delete Account" in the app; related personal data handling follows the Privacy Policy.',
    es: 'Los usuarios pueden eliminar su cuenta libremente en cualquier momento desde "Configuración &gt; Eliminar cuenta" en la app; el tratamiento de los datos personales relacionados sigue la Política de Privacidad.',
    zh: '用户可随时通过应用内"设置 &gt; 删除账户"自由注销，相关个人信息处理依照隐私政策执行。',
    ja: '利用者はアプリ内の「設定 &gt; アカウント削除」からいつでも自由に退会でき、関連する個人情報の取り扱いはプライバシーポリシーに従います。',
  },
  "terms.a8.title": { ko: "제8조 (면책)", en: "Article 8 (Disclaimer)", es: "Artículo 8 (Exención de responsabilidad)", zh: "第8条（免责）", ja: "第8条（免責）" },
  "terms.a8.body": {
    ko: "회사는 이용자 간 만남, 대화, 오프라인 활동에서 발생하는 문제에 대해 직접적인 책임을 지지 않습니다. 이용자는 타인과의 만남에 있어 스스로의 안전에 유의해야 합니다.",
    en: "The Company is not directly liable for issues arising from meetings, conversations, or offline activity between users. Users must exercise their own caution and safety when meeting others.",
    es: "La Empresa no es directamente responsable de los problemas que surjan de encuentros, conversaciones o actividades fuera de línea entre usuarios. Los usuarios deben tener su propia precaución y seguridad al reunirse con otros.",
    zh: "对于用户之间见面、交流、线下活动中产生的问题，公司不承担直接责任。用户在与他人见面时应自行注意人身安全。",
    ja: "当社は利用者間の出会い、会話、オフラインでの活動において生じた問題について直接的な責任を負いません。利用者は他人との出会いにおいて自身の安全に注意する必要があります。",
  },
  "terms.a9.title": { ko: "제9조 (법 집행 협조)", en: "Article 9 (Law Enforcement Cooperation)", es: "Artículo 9 (Cooperación con las autoridades)", zh: "第9条（配合执法）", ja: "第9条（法執行機関への協力）" },
  "terms.a9.body": {
    ko: "회사는 인신매매, 성적 착취, 아동학대 등 불법행위가 의심되는 경우 관계 법령이 정하는 바에 따라 수사기관 등 관계 당국에 협조하며, 적법한 절차(영장, 소환장 등)에 따른 요청에 응합니다. 이용자는 서비스 내에서 이러한 불법행위를 발견한 경우 신고 기능 또는 제11조의 문의처를 통해 즉시 신고할 수 있습니다.",
    en: "The Company cooperates with law enforcement and other competent authorities in accordance with applicable law where trafficking, sexual exploitation, child abuse, or other illegal activity is suspected, and responds to requests made through valid legal process (e.g. warrants, subpoenas). Users who discover such illegal activity on the Service can report it immediately using the in-app report feature or the contact information in Article 11.",
    es: "La Empresa coopera con las autoridades policiales y otras autoridades competentes conforme a la ley aplicable cuando se sospeche trata de personas, explotación sexual, abuso infantil u otra actividad ilegal, y responde a solicitudes realizadas mediante un proceso legal válido (por ejemplo, órdenes judiciales o citaciones). Los usuarios que descubran dicha actividad ilegal en el Servicio pueden reportarla de inmediato mediante la función de reporte dentro de la app o la información de contacto del Artículo 11.",
    zh: "如怀疑存在人口贩卖、性剥削、虐待儿童等违法行为，本公司将依据适用法律配合执法机构等相关部门，并回应合法程序（如搜查令、传票）提出的要求。用户如在服务中发现此类违法行为，可通过应用内举报功能或第11条中的联系方式立即举报。",
    ja: "当社は、人身売買、性的搾取、児童虐待等の違法行為が疑われる場合、関連法令に従い捜査機関等の関係当局に協力し、正当な法的手続き（令状、召喚状等）による要請に応じます。利用者はサービス内でこうした違法行為を発見した場合、通報機能または第11条の連絡先を通じて直ちに通報できます。",
  },
  "terms.a10.title": { ko: "제10조 (환불 정책)", en: "Article 10 (Refund Policy)", es: "Artículo 10 (Política de reembolsos)", zh: "第10条（退款政策）", ja: "第10条（返金ポリシー）" },
  "terms.a10.body": {
    ko: "앱 내 결제(인앱결제)를 통한 구매는 App Store 또는 Google Play의 환불 정책 및 절차에 따릅니다. 웹사이트를 통해 직접 결제한 경우: AI 매칭권, 무제한 매칭 이용권 등 1회성 구매 상품은 결제일로부터 7일 이내이며 서비스가 실제로 사용되지 않은 건에 한해 제11조 문의처로 요청 시 환불이 가능합니다. 프리미엄 멤버십(구독) 상품은 앱 내에서 언제든 해지할 수 있으나, 이미 결제된 현재 결제 주기에 대한 환불은 제공되지 않습니다.",
    en: "Purchases made via in-app purchase follow the refund policies and procedures of the App Store or Google Play. For purchases made directly through the website: one-time products (such as AI Match packs or Unlimited Matching passes) may be refunded via the contact information in Article 11 within 7 days of payment, provided the service has not actually been used. The Premium Membership subscription can be canceled at any time in the app, but no refund is given for the current billing period already paid for.",
    es: "Las compras realizadas mediante compra dentro de la app siguen las políticas y procedimientos de reembolso de la App Store o Google Play. Para las compras realizadas directamente a través del sitio web: los productos de un solo uso (como los paquetes de AI Match o los pases de Matching Ilimitado) pueden reembolsarse mediante la información de contacto del Artículo 11 dentro de los 7 días posteriores al pago, siempre que el servicio no se haya utilizado realmente. La suscripción Premium Membership puede cancelarse en cualquier momento desde la app, pero no se reembolsa el período de facturación actual ya pagado.",
    zh: "通过应用内购买的商品，遵循App Store或Google Play各自的退款政策与流程。通过网站直接购买的：一次性商品（如AI匹配包、无限匹配通行证）如服务实际尚未使用，可在付款后7天内通过第11条联系方式申请退款。高级会员（订阅）可随时在应用内取消，但当前已付费的计费周期不予退款。",
    ja: "アプリ内課金（IAP）による購入は、App StoreまたはGoogle Playの返金ポリシーおよび手続きに従います。ウェブサイトを通じて直接決済した場合：AIマッチパックや無制限マッチングパスなどの単発商品は、サービスが実際に利用されていない場合に限り、決済日から7日以内に第11条の連絡先を通じて返金を請求できます。プレミアムメンバーシップ（サブスクリプション）はアプリ内でいつでも解約できますが、既に決済済みの当該請求期間分は返金されません。",
  },
  "terms.a11.title": { ko: "제11조 (문의처)", en: "Article 11 (Contact)", es: "Artículo 11 (Contacto)", zh: "第11条（联系方式）", ja: "第11条（お問い合わせ）" },
  "terms.a11.body": {
    ko: '약관 관련 문의: <a href="mailto:support@soodamate.com">support@soodamate.com</a>',
    en: 'Terms inquiries: <a href="mailto:support@soodamate.com">support@soodamate.com</a>',
    es: 'Consultas sobre los términos: <a href="mailto:support@soodamate.com">support@soodamate.com</a>',
    zh: '条款相关咨询：<a href="mailto:support@soodamate.com">support@soodamate.com</a>',
    ja: '規約に関するお問い合わせ：<a href="mailto:support@soodamate.com">support@soodamate.com</a>',
  },

  "shop.title": { ko: "프리미엄 상점", en: "Premium Shop", es: "Tienda Premium", zh: "高级商店", ja: "プレミアムショップ" },
  "shop.subtitle": {
    ko: '앱에서 "상점" 버튼으로 여기로 오셨다면 자동으로 로그인 상태예요. 결제는 Stripe로 안전하게 처리됩니다.',
    en: 'If you got here by tapping "Shop" in the app, you\'re already signed in. Payments are processed securely by Stripe.',
    es: 'Si llegaste aquí tocando "Tienda" en la app, ya tienes la sesión iniciada. Los pagos se procesan de forma segura con Stripe.',
    zh: '如果你是通过应用内的"商店"按钮进入的，系统已自动为你登录。付款由Stripe安全处理。',
    ja: 'アプリ内の「ショップ」ボタンからここに来た場合は、自動的にログイン状態になっています。決済はStripeにより安全に処理されます。',
  },
  "shop.authError": {
    ko: "로그인 정보가 없어요. 앱의 프로필 > 상점 화면에서 다시 열어주세요.",
    en: "We couldn't find your login. Please open this page again from Profile > Shop in the app.",
    es: "No encontramos tu sesión. Abre esta página de nuevo desde Perfil > Tienda en la app.",
    zh: "未找到登录信息，请从应用内的「我的 > 商店」重新打开此页面。",
    ja: "ログイン情報が見つかりません。アプリの「プロフィール > ショップ」からもう一度開いてください。",
  },
  "shop.notice": {
    ko: '결제 완료 후 크레딧은 앱에 바로 반영됩니다. 문의: <a href="mailto:support@soodamate.com">support@soodamate.com</a>',
    en: 'Your credits are added to the app right after payment completes. Questions: <a href="mailto:support@soodamate.com">support@soodamate.com</a>',
    es: 'Tus créditos se añaden a la app justo después de completar el pago. Preguntas: <a href="mailto:support@soodamate.com">support@soodamate.com</a>',
    zh: '付款完成后，积分将立即在应用内到账。咨询：<a href="mailto:support@soodamate.com">support@soodamate.com</a>',
    ja: '決済完了後、クレジットはすぐにアプリに反映されます。お問い合わせ：<a href="mailto:support@soodamate.com">support@soodamate.com</a>',
  },
  "shop.billedMonthly": { ko: "매달 결제", en: "Billed monthly", es: "Facturación mensual", zh: "按月扣款", ja: "毎月請求" },
  "shop.billedYearly": { ko: "매년 결제", en: "Billed yearly", es: "Facturación anual", zh: "按年扣款", ja: "毎年請求" },
  "shop.noRefundNotice": {
    ko: "멤버십은 앱 안에서 언제든 취소할 수 있어요. 이미 결제된 기간에 대한 환불은 제공되지 않습니다.",
    en: "Cancel your membership anytime in the app. No refunds are given for the current billing period.",
    es: "Puedes cancelar tu membresía en cualquier momento desde la app. No se otorgan reembolsos por el periodo de facturación actual.",
    zh: "你可以随时在应用内取消会员。当前计费周期不予退款。",
    ja: "メンバーシップはアプリ内でいつでも解約できます。今回の請求期間分の返金はありません。",
  },
  "shop.buyLabel": { ko: "구매", en: "Buy", es: "Comprar", zh: "购买", ja: "購入" },
  "shop.buyLoading": { ko: "이동 중...", en: "Redirecting...", es: "Redirigiendo...", zh: "跳转中...", ja: "移動中..." },
  "shop.checkoutError": {
    ko: "결제를 시작하지 못했어요. 잠시 후 다시 시도해주세요.",
    en: "Couldn't start checkout. Please try again in a moment.",
    es: "No se pudo iniciar el pago. Inténtalo de nuevo en un momento.",
    zh: "无法启动结算，请稍后再试。",
    ja: "決済を開始できませんでした。しばらくしてからもう一度お試しください。",
  },
  "shop.loadError": {
    ko: "상품을 불러오지 못했어요. 페이지를 새로고침해주세요.",
    en: "Couldn't load products. Please refresh the page.",
    es: "No se pudieron cargar los productos. Actualiza la página.",
    zh: "无法加载商品，请刷新页面。",
    ja: "商品を読み込めませんでした。ページを更新してください。",
  },
  "shop.sessionExpired": {
    ko: "로그인이 만료됐어요. 앱에서 상점을 다시 열어주세요.",
    en: "Your session expired. Please reopen this page from Shop in the app.",
    es: "Tu sesión expiró. Vuelve a abrir esta página desde Tienda en la app.",
    zh: "登录已过期，请在应用内重新打开商店页面。",
    ja: "ログインの有効期限が切れました。アプリ内のショップからもう一度開いてください。",
  },

  "shop.explainerTitle": { ko: "뭐가 다른가요?", en: "What's the difference?", es: "¿Cuál es la diferencia?", zh: "有什么区别？", ja: "何が違うの？" },
  "shop.explainerAiMatch.title": { ko: "AI 매칭", en: "AI Matching", es: "Match con IA", zh: "AI匹配", ja: "AIマッチング" },
  "shop.explainerAiMatch.body": {
    ko: "블라인드 채팅에서 대기 없이 바로 매칭돼요 — 관심사·나이·거리를 분석해서 가장 잘 맞는 상대를 찾아드려요.",
    en: "Skip the Blind Chat queue — get matched instantly with whoever's the best fit, based on interests, age, and distance.",
    es: "Sáltate la cola de Chat a ciegas — te empareja al instante con quien mejor encaje, según intereses, edad y distancia.",
    zh: "跳过盲聊排队，根据兴趣、年龄和距离，立即为你匹配最合适的对象。",
    ja: "ブラインドチャットの順番待ちなしで、興味・年齢・距離をもとに最も相性の良い相手とすぐにマッチングします。",
  },
  "shop.explainerUnlimitedMatching.title": { ko: "무제한 매칭", en: "Unlimited Matching", es: "Matching ilimitado", zh: "无限匹配", ja: "無制限マッチング" },
  "shop.explainerUnlimitedMatching.body": {
    ko: "블라인드 채팅의 하루 무료 매칭 횟수 제한 없이 계속 이용할 수 있어요.",
    en: "No daily cap on Blind Chat matches — keep matching as much as you want.",
    es: "Sin límite diario de matches en Chat a ciegas — sigue emparejándote todo lo que quieras.",
    zh: "盲聊不再受每日免费匹配次数限制，可以持续匹配。",
    ja: "ブラインドチャットの1日の無料マッチング回数制限なしで、いつでもマッチングできます。",
  },
  "shop.explainerPremium.title": { ko: "프리미엄", en: "Premium", es: "Premium", zh: "高级会员", ja: "プレミアム" },
  "shop.explainerPremium.body": {
    ko: "구독하는 동안 계속 적용되는 혜택이에요 — 블라인드 채팅을 하루 횟수 제한 없이 무제한으로 이용할 수 있어요.",
    en: "An ongoing subscription — unlimited Blind Chat matching, with no daily cap, for as long as you're subscribed.",
    es: "Una suscripción continua — matching ilimitado en Chat a ciegas, sin límite diario, mientras estés suscrito.",
    zh: "持续生效的订阅——订阅期间可无限次盲聊匹配，不受每日次数限制。",
    ja: "継続的なサブスクリプションです — 契約中はブラインドチャットが1日の回数制限なしで使い放題になります。",
  },

  "shop.product.membership_monthly.name": { ko: "프리미엄 멤버십", en: "Premium Membership", es: "Membresía Premium", zh: "高级会员", ja: "プレミアム会員" },
  "shop.product.membership_monthly.desc": {
    ko: "블라인드 채팅 무제한 매칭 — 매달 자동 갱신돼요.",
    en: "Unlimited Blind Chat matching — renews monthly.",
    es: "Matching ilimitado en Chat a ciegas — se renueva cada mes.",
    zh: "无限次盲聊匹配——每月自动续费。",
    ja: "ブラインドチャット無制限マッチング — 毎月自動更新されます。",
  },
  "shop.product.membership_yearly.name": { ko: "프리미엄 멤버십", en: "Premium Membership", es: "Membresía Premium", zh: "高级会员", ja: "プレミアム会員" },
  "shop.product.membership_yearly.desc": {
    ko: "블라인드 채팅 무제한 매칭 — 매년 자동 갱신되고 월간 결제보다 저렴해요.",
    en: "Unlimited Blind Chat matching — renews yearly, cheaper than paying monthly.",
    es: "Matching ilimitado en Chat a ciegas — se renueva cada año, más barato que mes a mes.",
    zh: "无限次盲聊匹配——每年自动续费，比按月付费更划算。",
    ja: "ブラインドチャット無制限マッチング — 毎年自動更新、月払いよりお得です。",
  },

  "shop.product.ai_match_pack_1.name": { ko: "AI 매칭권 1회", en: "AI Match x1", es: "1 Match con IA", zh: "AI匹配 x1", ja: "AIマッチ ×1" },
  "shop.product.ai_match_pack_1.desc": {
    ko: "블라인드 채팅 대기 없이, 나와 가장 잘 맞는 상대와 바로 매칭돼요.",
    en: "Skip the Blind Chat queue — get matched instantly with your best fit.",
    es: "Sáltate la cola de Chat a ciegas — te empareja al instante con tu mejor match.",
    zh: "跳过盲聊排队，立即匹配最合适的对象。",
    ja: "ブラインドチャットの順番待ちなしで、最も相性の良い相手とすぐマッチング。",
  },
  "shop.product.ai_match_pack_5.name": { ko: "AI 매칭권 5회", en: "AI Match x5", es: "5 Matches con IA", zh: "AI匹配 x5", ja: "AIマッチ ×5" },
  "shop.product.ai_match_pack_5.desc": {
    ko: "블라인드 채팅 대기 없이, 나와 가장 잘 맞는 상대와 바로 매칭돼요.",
    en: "Skip the Blind Chat queue — get matched instantly with your best fit.",
    es: "Sáltate la cola de Chat a ciegas — te empareja al instante con tu mejor match.",
    zh: "跳过盲聊排队，立即匹配最合适的对象。",
    ja: "ブラインドチャットの順番待ちなしで、最も相性の良い相手とすぐマッチング。",
  },
  "shop.product.unlimited_matching_week.name": {
    ko: "무제한 매칭 1주일", en: "Unlimited Matching — 1 week", es: "Matching ilimitado — 1 semana",
    zh: "无限匹配 — 1周", ja: "無制限マッチング — 1週間",
  },
  "shop.product.unlimited_matching_week.desc": {
    ko: "1주일 동안 블라인드 채팅 하루 무료 매칭 횟수 제한이 사라져요.",
    en: "No daily Blind Chat match cap for 1 week.",
    es: "Sin límite diario de matches en Chat a ciegas durante 1 semana.",
    zh: "1周内盲聊不再受每日免费匹配次数限制。",
    ja: "1週間、ブラインドチャットの1日の無料マッチング回数制限がなくなります。",
  },
  "shop.product.unlimited_matching_month.name": {
    ko: "무제한 매칭 1개월", en: "Unlimited Matching — 1 month", es: "Matching ilimitado — 1 mes",
    zh: "无限匹配 — 1个月", ja: "無制限マッチング — 1ヶ月",
  },
  "shop.product.unlimited_matching_month.desc": {
    ko: "1개월 동안 블라인드 채팅 하루 무료 매칭 횟수 제한이 사라져요.",
    en: "No daily Blind Chat match cap for 1 month.",
    es: "Sin límite diario de matches en Chat a ciegas durante 1 mes.",
    zh: "1个月内盲聊不再受每日免费匹配次数限制。",
    ja: "1ヶ月間、ブラインドチャットの1日の無料マッチング回数制限がなくなります。",
  },

  "shopSuccess.title": { ko: "결제가 완료됐어요!", en: "Payment complete!", es: "¡Pago completado!", zh: "支付已完成！", ja: "決済が完了しました！" },
  "shopSuccess.body": {
    ko: "구매하신 크레딧이 곧 앱에 반영됩니다. 앱으로 돌아가서 확인해보세요.",
    en: "Your credits will be added shortly. Head back to the app to check.",
    es: "Tus créditos se añadirán en breve. Vuelve a la app para comprobarlo.",
    zh: "您购买的积分即将到账，请返回应用查看。",
    ja: "ご購入いただいたクレジットはまもなく反映されます。アプリに戻ってご確認ください。",
  },
  "shopSuccess.backBtn": { ko: "앱으로 돌아가기", en: "Back to the app", es: "Volver a la app", zh: "返回应用", ja: "アプリに戻る" },
};

function currentLang() {
  const saved = localStorage.getItem("sooda_lang");
  if (saved && SUPPORTED_LANGS.includes(saved)) return saved;
  const browserLang = (navigator.language || "en").slice(0, 2);
  return SUPPORTED_LANGS.includes(browserLang) ? browserLang : "en";
}

function applyLang(lang) {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const entry = translations[el.getAttribute("data-i18n")];
    if (entry && entry[lang]) el.textContent = entry[lang];
  });
  document.querySelectorAll("[data-i18n-html]").forEach((el) => {
    const entry = translations[el.getAttribute("data-i18n-html")];
    if (entry && entry[lang]) el.innerHTML = entry[lang];
  });
  document.querySelectorAll("[data-lang-option]").forEach((el) => {
    el.classList.toggle("active", el.getAttribute("data-lang-option") === lang);
  });
  localStorage.setItem("sooda_lang", lang);
}

function initLangSwitcher() {
  const switcher = document.querySelector("[data-lang-switcher]");
  if (!switcher) return;
  switcher.innerHTML = SUPPORTED_LANGS.map(
    (l) => `<button type="button" data-lang-option="${l}">${LANG_LABELS[l]}</button>`
  ).join("");
  switcher.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lang-option]");
    if (btn) applyLang(btn.getAttribute("data-lang-option"));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initLangSwitcher();
  applyLang(currentLang());
});
