// Lightweight vanilla-JS i18n: no build step, matches this site's existing
// plain HTML/CSS/JS convention. Elements opt in via data-i18n="key" (sets
// textContent) or data-i18n-html="key" (sets innerHTML, for strings that
// need embedded markup like the accent <span> in the hero title).
const SUPPORTED_LANGS = ["ko", "en", "es", "zh", "ja"];
const LANG_LABELS = { ko: "한국어", en: "English", es: "Español", zh: "中文", ja: "日本語" };

const translations = {
  "nav.features": { ko: "기능", en: "Features", es: "Funciones", zh: "功能", ja: "機能" },
  "nav.rule": { ko: "매칭 방식", en: "How Matching Works", es: "Cómo funciona", zh: "配对方式", ja: "マッチングの仕組み" },
  "nav.safety": { ko: "안전", en: "Safety", es: "Seguridad", zh: "安全保障", ja: "安全性" },
  "nav.screens": { ko: "스크린샷", en: "Screenshots", es: "Capturas", zh: "截图", ja: "スクリーンショット" },
  "nav.download": { ko: "다운로드", en: "Download", es: "Descargar", zh: "下载", ja: "ダウンロード" },

  "hero.eyebrow": {
    ko: "🇰🇷 한국 시장을 위한 데이팅 앱",
    en: "🇰🇷 A dating app built for Korea",
    es: "🇰🇷 Una app de citas creada para Corea",
    zh: "🇰🇷 专为韩国市场打造的约会应用",
    ja: "🇰🇷 韓国市場向けの出会いアプリ",
  },
  "hero.title": {
    ko: '스와이프 대신,<br /><span class="accent">확실한 버튼</span>으로 시작하는 수다',
    en: 'No more swiping.<br />Start the conversation with a <span class="accent">clear tap</span>',
    es: 'Nada de deslizar.<br />Empieza la charla con un <span class="accent">toque claro</span>',
    zh: '告别滑动，<br />用<span class="accent">明确的按钮</span>开启对话',
    ja: 'スワイプはもう不要。<br /><span class="accent">はっきりしたボタン</span>で会話を始めよう',
  },
  "hero.subtitle": {
    ko: "실수로 넘기는 스와이프는 이제 그만. 좋아요·패스·슈퍼좋아요 버튼으로 또렷하게 의사표현하고, 매칭되면 바로 실시간 채팅으로 진짜 대화를 시작하세요.",
    en: "No more accidental swipes. Tap Like, Pass, or Super Like to say exactly what you mean — then jump straight into real-time chat the moment you match.",
    es: "Se acabaron los deslizamientos accidentales. Toca Me gusta, Pasar o Super Like para decir justo lo que piensas, y empieza a chatear en tiempo real en cuanto haya match.",
    zh: "再也不会误滑。用喜欢、跳过、超级喜欢按钮清楚表达心意，配对成功后立即开始实时聊天。",
    ja: "誤スワイプとはもうお別れ。いいね・パス・スーパーいいねボタンではっきり意思表示。マッチしたらすぐリアルタイムチャットで会話を始められます。",
  },
  "hero.storeSoon": { ko: "출시 예정", en: "Coming soon", es: "Próximamente", zh: "即将上线", ja: "近日公開" },
  "hero.trust1": { ko: "만 18세 이상만 이용 가능", en: "18+ only", es: "Solo mayores de 18 años", zh: "仅限18岁以上", ja: "18歳以上のみ利用可能" },
  "hero.trust2": { ko: "실시간 신고·차단", en: "Real-time report & block", es: "Reporte y bloqueo en tiempo real", zh: "实时举报与拉黑", ja: "リアルタイム通報・ブロック" },
  "hero.trust3": { ko: "카카오·구글 간편 로그인", en: "Sign in with Kakao or Google", es: "Inicia sesión con Kakao o Google", zh: "支持Kakao、谷歌快捷登录", ja: "カカオ・Googleで簡単ログイン" },
  "hero.matchToast": { ko: "💛 It's a Match!", en: "💛 It's a Match!", es: "💛 ¡Es un Match!", zh: "💛 配对成功！", ja: "💛 マッチしました！" },
  "hero.chatToast": { ko: "💬 실시간 채팅 연결됨", en: "💬 Live chat connected", es: "💬 Chat en vivo conectado", zh: "💬 实时聊天已连接", ja: "💬 リアルタイムチャット接続中" },
  "hero.cardDistance": { ko: "2km 이내", en: "Within 2km", es: "A 2 km", zh: "2公里内", ja: "2km圏内" },
  "hero.cardName": { ko: "지은, 27", en: "Jieun, 27", es: "Jieun, 27", zh: "智恩, 27岁", ja: "ジウン, 27歳" },
  "hero.cardBio": {
    ko: "주말엔 등산, 평일엔 카페 탐방 🌿",
    en: "Hiking on weekends, café-hopping on weekdays 🌿",
    es: "Senderismo los fines de semana, cafés entre semana 🌿",
    zh: "周末爬山，平日探店咖啡馆 🌿",
    ja: "週末は登山、平日はカフェ巡り 🌿",
  },

  "features.head.title": { ko: "왜 수다메이트일까요", en: "Why SooDa Mate", es: "Por qué SooDa Mate", zh: "为什么选择数搭伴侣", ja: "なぜ数多メイトなのか" },
  "features.head.sub": {
    ko: "불편한 스와이프 대신 명확한 선택, 그리고 진짜 대화로 이어지는 경험을 설계했습니다.",
    en: "We designed clear choices instead of awkward swiping — and an experience that actually leads to real conversation.",
    es: "Diseñamos elecciones claras en vez de deslizamientos incómodos, y una experiencia que realmente lleva a conversaciones reales.",
    zh: "我们用明确的选择取代尴尬的滑动，打造真正能促成对话的体验。",
    ja: "気まずいスワイプの代わりに、はっきりした選択と本当の会話につながる体験を設計しました。",
  },
  "feature.1.title": { ko: "버튼으로 편하게", en: "Comfortable, button-based", es: "Cómodo, con botones", zh: "按钮操作更安心", ja: "ボタンで気軽に" },
  "feature.1.body": {
    ko: "좋아요·패스·슈퍼좋아요 버튼으로 명확하게 의사표현. 실수로 밀어서 놓치는 인연이 없어요.",
    en: "Like, Pass, or Super Like — say exactly what you mean. No more missed connections from an accidental swipe.",
    es: "Me gusta, Pasar o Super Like: di exactamente lo que piensas. Nada de conexiones perdidas por un deslizamiento accidental.",
    zh: "喜欢、跳过、超级喜欢，清楚表达心意，不再因误滑而错过缘分。",
    ja: "いいね・パス・スーパーいいねで意思をはっきり表現。誤操作で縁を逃すことはありません。",
  },
  "feature.2.title": { ko: "실시간 채팅", en: "Real-time chat", es: "Chat en tiempo real", zh: "实时聊天", ja: "リアルタイムチャット" },
  "feature.2.body": {
    ko: "매칭되는 순간 바로 대화를 시작할 수 있는 실시간 채팅으로, 어색한 정적 없이 이어집니다.",
    en: "The moment you match, jump straight into live conversation — no awkward silence in between.",
    es: "En cuanto haya match, pasa directo a una conversación en vivo, sin silencios incómodos.",
    zh: "配对瞬间即可开始实时对话，不留尴尬的沉默。",
    ja: "マッチした瞬間からリアルタイムで会話がスタート。気まずい沈黙はありません。",
  },
  "feature.3.title": { ko: "슈퍼좋아요 & 부스트", en: "Super Like & Boost", es: "Super Like y Boost", zh: "超级喜欢与曝光加速", ja: "スーパーいいね＆ブースト" },
  "feature.3.body": {
    ko: "마음에 드는 상대에게 특별하게 눈에 띄고 싶다면 슈퍼좋아요와 부스트로 우선 노출되세요.",
    en: "Want to stand out to someone special? Use Super Like and Boost to get priority visibility.",
    es: "¿Quieres destacar ante alguien especial? Usa Super Like y Boost para tener prioridad.",
    zh: "想在心仪对象面前脱颖而出？用超级喜欢和曝光加速获得优先展示。",
    ja: "気になる相手に特別にアピールしたいなら、スーパーいいねとブーストで優先表示。",
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
  "feature.6.title": { ko: "인코그니토 & 여행 모드", en: "Incognito & Travel mode", es: "Modo incógnito y viaje", zh: "隐身模式与旅行模式", ja: "シークレット＆旅行モード" },
  "feature.6.body": {
    ko: "조용히 둘러보고 싶을 땐 인코그니토, 다른 지역 인연이 궁금할 땐 여행 모드를 켜보세요.",
    en: "Browse quietly with Incognito, or turn on Travel mode to meet people in another city.",
    es: "Explora en privado con el modo Incógnito, o activa el modo Viaje para conocer gente en otra ciudad.",
    zh: "想安静浏览就开启隐身模式，想认识异地的人就打开旅行模式。",
    ja: "静かに閲覧したい時はシークレットモード、他の地域の出会いが気になる時は旅行モードを。",
  },

  "how.head.title": { ko: "시작하는 방법", en: "How to get started", es: "Cómo empezar", zh: "如何开始", ja: "始め方" },
  "how.head.sub": {
    ko: "가입부터 첫 대화까지, 3단계면 충분합니다.",
    en: "From sign-up to your first conversation, it only takes 3 steps.",
    es: "Desde el registro hasta tu primera conversación, solo 3 pasos.",
    zh: "从注册到第一次对话，只需三步。",
    ja: "登録から最初の会話まで、たった3ステップ。",
  },
  "how.1.title": { ko: "3초 로그인", en: "3-second login", es: "Inicio de sesión en 3 segundos", zh: "3秒登录", ja: "3秒ログイン" },
  "how.1.body": {
    ko: "카카오, 구글, 이메일 중 편한 방법으로 가입하고 프로필을 완성하세요.",
    en: "Sign up with Kakao, Google, or email — whichever's easiest — then finish your profile.",
    es: "Regístrate con Kakao, Google o correo, el que prefieras, y completa tu perfil.",
    zh: "选择Kakao、谷歌或邮箱注册，完善你的个人主页。",
    ja: "カカオ、Google、メールの好きな方法で登録し、プロフィールを完成させましょう。",
  },
  "how.2.title": { ko: "버튼으로 둘러보기", en: "Browse with a tap", es: "Explora con un toque", zh: "按钮浏览", ja: "ボタンで見て回る" },
  "how.2.body": {
    ko: "추천된 프로필을 보고 좋아요·패스·슈퍼좋아요 버튼으로 선택하세요.",
    en: "Look through recommended profiles and choose with Like, Pass, or Super Like.",
    es: "Mira los perfiles recomendados y elige con Me gusta, Pasar o Super Like.",
    zh: "查看推荐的用户资料，用喜欢、跳过、超级喜欢做出选择。",
    ja: "おすすめのプロフィールを見て、いいね・パス・スーパーいいねで選びましょう。",
  },
  "how.3.title": { ko: "매칭 후 대화", en: "Match, then chat", es: "Match y luego chatea", zh: "配对后开聊", ja: "マッチしたら会話" },
  "how.3.body": {
    ko: "서로 좋아요를 누르면 매칭! 바로 실시간 채팅으로 대화를 시작하세요.",
    en: "When you both say Like, it's a match! Start chatting in real time right away.",
    es: "Cuando ambos se dan Me gusta, ¡es match! Empieza a chatear en tiempo real de inmediato.",
    zh: "双方都喜欢即可配对！立即开始实时聊天。",
    ja: "お互いにいいねすればマッチ成立！すぐにリアルタイムチャットで会話を始められます。",
  },

  "rule.badge": { ko: "✨ 여성을 위한 안전한 시작", en: "✨ A safer start for women", es: "✨ Un comienzo más seguro para ellas", zh: "✨ 为女性打造的安心开场", ja: "✨ 女性のための安心スタート" },
  "rule.title": {
    ko: "먼저 말 걸어야 하는 부담,<br />이제 지워드릴게요",
    en: "The pressure to message first?<br />Consider it gone",
    es: "¿La presión de escribir primero?<br />Considérala resuelta",
    zh: "先开口的压力，<br />我们帮你卸下",
    ja: "先にメッセージを送るプレッシャー、<br />もうなくなります",
  },
  "rule.p1": {
    ko: "남녀가 매칭되면 여성 회원이 먼저 대화를 시작할 수 있어요. 원치 않는 연락으로부터의 부담을 줄이고, 대화를 시작할 준비가 됐을 때 편하게 먼저 말을 건넬 수 있도록 설계했습니다.",
    en: "When a man and woman match, she gets to send the first message. It's designed to ease the pressure of unwanted contact — she can reach out whenever she's ready.",
    es: "Cuando hacen match un hombre y una mujer, ella puede enviar el primer mensaje. Está pensado para aliviar la presión de contactos no deseados: ella escribe cuando esté lista.",
    zh: "男女配对成功后，由女性会员优先发起对话，减轻不必要联系带来的压力，让她在准备好时从容开口。",
    ja: "男女がマッチした場合、女性会員が先にメッセージを送れます。望まない連絡のプレッシャーを減らし、準備ができた時に気軽に話しかけられるよう設計しました。",
  },
  "rule.p2": {
    ko: "같은 성별 간 매칭이나 성별 무관 매칭은 누구나 먼저 대화를 시작할 수 있어요.",
    en: "For same-gender or gender-neutral matches, either person can message first.",
    es: "En matches del mismo género o sin preferencia de género, cualquiera puede escribir primero.",
    zh: "同性配对或性别不限的配对，双方均可先发起对话。",
    ja: "同性同士やジェンダーを問わないマッチでは、どちらからでも先にメッセージを送れます。",
  },
  "rule.timeline1.title": { ko: "매칭 성사", en: "Match made", es: "Match hecho", zh: "配对成功", ja: "マッチ成立" },
  "rule.timeline1.body": {
    ko: "서로 좋아요를 누르면 매칭이 만들어져요.",
    en: "When you both tap Like, a match is created.",
    es: "Cuando ambos tocan Me gusta, se crea un match.",
    zh: "双方都点击喜欢即可建立配对。",
    ja: "お互いにいいねすればマッチが成立します。",
  },
  "rule.timeline2.title": { ko: "24시간의 기회", en: "A 24-hour window", es: "Una ventana de 24 horas", zh: "24小时机会窗口", ja: "24時間のチャンス" },
  "rule.timeline2.body": {
    ko: "남녀 매칭이라면 여성 회원에게 먼저 대화를 시작할 24시간이 주어져요.",
    en: "For a man/woman match, she has 24 hours to send the first message.",
    es: "En un match hombre/mujer, ella tiene 24 horas para enviar el primer mensaje.",
    zh: "男女配对时，女性会员有24小时可优先发起对话。",
    ja: "男女のマッチの場合、女性会員には先にメッセージを送る24時間が与えられます。",
  },
  "rule.timeline3.title": { ko: "대화 시작!", en: "Let's chat!", es: "¡A chatear!", zh: "开始聊天！", ja: "会話スタート！" },
  "rule.timeline3.body": {
    ko: "첫 메시지가 오면 이후엔 누구나 자유롭게 대화할 수 있어요.",
    en: "Once the first message is sent, anyone can chat freely from then on.",
    es: "Una vez enviado el primer mensaje, ambos pueden chatear libremente.",
    zh: "第一条消息发出后，双方即可自由聊天。",
    ja: "最初のメッセージが送られたら、以降は誰でも自由に会話できます。",
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
  "screens.discover": { ko: "Discover<br />버튼으로 둘러보기", en: "Discover<br />Browse with a tap", es: "Descubrir<br />Explora con un toque", zh: "发现<br />按钮浏览", ja: "ディスカバー<br />ボタンで見て回る" },
  "screens.match": { ko: "It's a Match!", en: "It's a Match!", es: "¡Es un Match!", zh: "配对成功！", ja: "マッチしました！" },
  "screens.chat": { ko: "실시간 채팅", en: "Live chat", es: "Chat en vivo", zh: "实时聊天", ja: "リアルタイムチャット" },

  "cta.title": { ko: "지금 바로 시작하세요", en: "Get started today", es: "Empieza hoy mismo", zh: "现在就开始吧", ja: "今すぐ始めよう" },
  "cta.body": {
    ko: "수다메이트는 곧 App Store와 Google Play에 출시됩니다.",
    en: "SooDa Mate is launching soon on the App Store and Google Play.",
    es: "SooDa Mate llega pronto a App Store y Google Play.",
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
    en: 'SooDaList ("the Company") operates the SooDa Mate app ("the Service") and takes your privacy seriously. This policy explains what personal data we collect, why, how long we keep it, who we share it with, and your rights.',
    es: 'SooDaList ("la Empresa") opera la app SooDa Mate ("el Servicio") y se toma en serio tu privacidad. Esta política explica qué datos personales recopilamos, por qué, cuánto tiempo los conservamos, con quién los compartimos y cuáles son tus derechos.',
    zh: 'SooDaList（"公司"）运营数搭伴侣应用（"服务"），高度重视用户隐私。本政策说明我们收集哪些个人信息、收集目的、保存期限、第三方共享情况以及用户享有的权利。',
    ja: 'SooDaList（以下「当社」）は数多メイトアプリ（以下「本サービス」）を運営しており、利用者の個人情報を大切に取り扱います。本方針では、収集する個人情報の項目、利用目的、保管期間、第三者提供、および利用者の権利について説明します。',
  },
  "privacy.h1": { ko: "1. 수집하는 개인정보 항목", en: "1. Personal Data We Collect", es: "1. Datos personales que recopilamos", zh: "1. 我们收集的个人信息", ja: "1. 収集する個人情報の項目" },
  "privacy.s1.li1": {
    ko: "<strong>계정 정보</strong> — 이메일 주소, 비밀번호(해시 저장), 또는 구글/카카오 소셜 로그인 시 제공되는 식별자·이메일",
    en: "<strong>Account info</strong> — email address, password (stored hashed), or the identifier/email provided by Google/Kakao social login",
    es: "<strong>Datos de cuenta</strong> — correo electrónico, contraseña (almacenada como hash), o el identificador/correo proporcionado por el inicio de sesión social de Google/Kakao",
    zh: "<strong>账户信息</strong> — 电子邮箱、密码（哈希存储），或谷歌/Kakao社交登录提供的标识符和邮箱",
    ja: "<strong>アカウント情報</strong> — メールアドレス、パスワード（ハッシュ化して保存）、またはGoogle/カカオのソーシャルログイン時に提供される識別子・メールアドレス",
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
  "privacy.s4.li1": { ko: "<strong>Google / Kakao</strong> — 소셜 로그인 인증", en: "<strong>Google / Kakao</strong> — social login authentication", es: "<strong>Google / Kakao</strong> — autenticación de inicio de sesión social", zh: "<strong>谷歌 / Kakao</strong> — 社交登录认证", ja: "<strong>Google / カカオ</strong> — ソーシャルログイン認証" },
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
    ko: '개인정보 관련 문의: <a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a> (연락처는 정식 출시 전 실제 주소로 교체 예정)',
    en: 'Privacy inquiries: <a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a> (to be replaced with a real address before official launch)',
    es: 'Consultas sobre privacidad: <a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a> (se reemplazará por una dirección real antes del lanzamiento oficial)',
    zh: '隐私相关咨询：<a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a>（正式上线前将替换为真实联系地址）',
    ja: '個人情報に関するお問い合わせ：<a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a>（正式リリース前に実際のアドレスに変更予定）',
  },

  "deleteAccount.title": { ko: "계정 삭제 안내", en: "Delete Your Account", es: "Eliminar tu cuenta", zh: "删除账户说明", ja: "アカウント削除について" },
  "deleteAccount.intro": {
    ko: "수다메이트(SooDa Mate) 앱을 운영하는 SooDaList는 이용자가 언제든지 본인의 계정과 데이터를 삭제할 수 있도록 안내합니다.",
    en: "SooDaList, which operates the SooDa Mate app, lets you delete your account and data at any time.",
    es: "SooDaList, que opera la app SooDa Mate, te permite eliminar tu cuenta y tus datos en cualquier momento.",
    zh: "运营数搭伴侣（SooDa Mate）应用的SooDaList，让你可以随时删除自己的账户和数据。",
    ja: "SooDa Mateアプリを運営するSooDaListは、いつでもアカウントとデータを削除できるようご案内します。",
  },
  "deleteAccount.h1": { ko: "1. 앱에서 직접 삭제하기", en: "1. Delete in the app", es: "1. Eliminar desde la app", zh: "1. 在应用内删除", ja: "1. アプリ内で削除する" },
  "deleteAccount.step1": {
    ko: "수다메이트 앱을 열고 로그인합니다.",
    en: "Open the SooDa Mate app and log in.",
    es: "Abre la app SooDa Mate e inicia sesión.",
    zh: "打开数搭伴侣应用并登录。",
    ja: "SooDa Mateアプリを開いてログインします。",
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
    ko: '로그인할 수 없거나 앱을 삭제하셨다면, <a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a>으로 가입 시 사용한 이메일 주소와 함께 계정 삭제를 요청해 주세요. 본인 확인 후 처리해 드립니다.',
    en: 'If you can\'t log in or no longer have the app installed, email <a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a> with the address you signed up with to request deletion. We\'ll verify your identity and process it.',
    es: 'Si no puedes iniciar sesión o ya no tienes la app instalada, escribe a <a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a> con el correo con el que te registraste para solicitar la eliminación. Verificaremos tu identidad y lo procesaremos.',
    zh: '如果无法登录或已卸载应用，请发送邮件至 <a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a>，附上注册时使用的邮箱地址以申请删除。我们核实身份后会为你处理。',
    ja: 'ログインできない、またはアプリをすでに削除した場合は、<a href="mailto:privacy@soodamate.example.com">privacy@soodamate.example.com</a> に登録時のメールアドレスを添えて削除をご依頼ください。本人確認の上、対応いたします。',
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
    en: 'These Terms set out the rights, obligations, and responsibilities between SooDaList ("the Company") and users regarding the use of the SooDa Mate app service ("the Service").',
    es: 'Estos Términos establecen los derechos, obligaciones y responsabilidades entre SooDaList ("la Empresa") y los usuarios en relación con el uso del servicio de la app SooDa Mate ("el Servicio").',
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
  "terms.a3.li2": { ko: "이메일/비밀번호, 구글, 카카오 중 하나 이상의 방법으로 가입할 수 있습니다.", en: "You may sign up using email/password, Google, or Kakao, or more than one.", es: "Puedes registrarte usando correo/contraseña, Google o Kakao, o más de uno.", zh: "可通过邮箱/密码、谷歌、Kakao中的一种或多种方式注册。", ja: "メール/パスワード、Google、カカオのいずれか一つ以上の方法で登録できます。" },
  "terms.a3.li3": { ko: "타인의 정보를 도용하거나 허위 정보로 프로필을 작성하는 행위는 금지됩니다.", en: "Impersonating someone else or creating a profile with false information is prohibited.", es: "Está prohibido suplantar a otra persona o crear un perfil con información falsa.", zh: "禁止盗用他人信息或以虚假信息编写个人主页。", ja: "他人の情報を盗用したり、虚偽の情報でプロフィールを作成したりする行為は禁止です。" },
  "terms.a4.title": { ko: "제4조 (이용자의 의무)", en: "Article 4 (User Obligations)", es: "Artículo 4 (Obligaciones del usuario)", zh: "第4条（用户义务）", ja: "第4条（利用者の義務）" },
  "terms.a4.intro": { ko: "이용자는 다음 행위를 해서는 안 됩니다.", en: "Users must not do the following:", es: "Los usuarios no deben hacer lo siguiente:", zh: "用户不得从事以下行为：", ja: "利用者は以下の行為をしてはなりません。" },
  "terms.a4.li1": { ko: "허위 프로필 작성 또는 타인을 사칭하는 행위", en: "Creating a false profile or impersonating another person", es: "Crear un perfil falso o suplantar a otra persona", zh: "编写虚假个人主页或冒充他人", ja: "虚偽のプロフィールを作成したり、他人になりすましたりする行為" },
  "terms.a4.li2": { ko: "다른 이용자에 대한 욕설, 희롱, 스토킹, 위협 등 부적절한 행위", en: "Abuse, harassment, stalking, threats, or other inappropriate conduct toward other users", es: "Insultos, acoso, acecho, amenazas u otra conducta inapropiada hacia otros usuarios", zh: "对其他用户辱骂、骚扰、跟踪、威胁等不当行为", ja: "他の利用者に対する暴言、嫌がらせ、ストーカー行為、脅迫等の不適切な行為" },
  "terms.a4.li3": { ko: "상업적 광고, 스팸, 사기성 메시지 전송", en: "Sending commercial advertising, spam, or fraudulent messages", es: "Envío de publicidad comercial, spam o mensajes fraudulentos", zh: "发送商业广告、垃圾信息或欺诈性消息", ja: "商業広告、スパム、詐欺的メッセージの送信" },
  "terms.a4.li4": { ko: "미성년자를 대상으로 하거나 미성년자가 이용하는 행위", en: "Targeting minors, or use of the Service by minors", es: "Dirigirse a menores de edad, o el uso del Servicio por menores", zh: "以未成年人为对象或未成年人使用本服务", ja: "未成年者を対象とする、または未成年者が利用する行為" },
  "terms.a4.li5": { ko: "서비스의 정상적인 운영을 방해하는 행위(자동화 도구 사용 등)", en: "Interfering with normal operation of the Service (e.g. using automated tools)", es: "Interferir con el funcionamiento normal del Servicio (p. ej. uso de herramientas automatizadas)", zh: "妨碍服务正常运营的行为（如使用自动化工具等）", ja: "本サービスの正常な運営を妨害する行為（自動化ツールの使用等）" },
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
  "terms.a9.title": { ko: "제9조 (문의처)", en: "Article 9 (Contact)", es: "Artículo 9 (Contacto)", zh: "第9条（联系方式）", ja: "第9条（お問い合わせ）" },
  "terms.a9.body": {
    ko: '약관 관련 문의: <a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a> (연락처는 정식 출시 전 실제 주소로 교체 예정)',
    en: 'Terms inquiries: <a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a> (to be replaced with a real address before official launch)',
    es: 'Consultas sobre los términos: <a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a> (se reemplazará por una dirección real antes del lanzamiento oficial)',
    zh: '条款相关咨询：<a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a>（正式上线前将替换为真实联系地址）',
    ja: '規約に関するお問い合わせ：<a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a>（正式リリース前に実際のアドレスに変更予定）',
  },

  "shop.title": { ko: "슈퍼좋아요 & 부스트", en: "Super Like & Boost", es: "Super Like y Boost", zh: "超级喜欢与曝光加速", ja: "スーパーいいね＆ブースト" },
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
    ko: '결제 완료 후 크레딧은 앱에 바로 반영됩니다. 문의: <a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a>',
    en: 'Your credits are added to the app right after payment completes. Questions: <a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a>',
    es: 'Tus créditos se añaden a la app justo después de completar el pago. Preguntas: <a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a>',
    zh: '付款完成后，积分将立即在应用内到账。咨询：<a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a>',
    ja: '決済完了後、クレジットはすぐにアプリに反映されます。お問い合わせ：<a href="mailto:support@soodamate.example.com">support@soodamate.example.com</a>',
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
