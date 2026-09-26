# 스픽(Speak) 커리큘럼·시나리오 조사

조사일: 2026-09-26
조사 시작점: https://www.speak.com/ko/content
조사자: Claude 에이전트(WebFetch·curl 기반 정적 조사)

## 0. 조사 방법과 한계

이 문서는 speak.com의 공개 페이지와 sitemap.xml만으로 작성함.
로그인 후에만 보이는 실제 앱 내부 화면(수업 진행 화면 등)은 조사 범위 밖임.
그러므로 이 문서의 "레슨 진행 흐름"은 마케팅 페이지가 설명하는 수준까지만 다룸.
일부 페이지는 자바스크립트로 데이터를 채우는 구조라 정적 조사로는 빈 결과만 나옴.
그 경우와 그 이유를 3장에 별도로 기록함.
문서 전체에서 사이트가 직접 밝히지 않은 추정치는 모두 "추정" 또는 "미확인"으로 표시함.

## 1. 요약

스픽은 학습 콘텐츠 소개 페이지에서 레벨을 CEFR A1~C1의 5단계로 나눔.
[출처: https://www.speak.com/ko/content]
같은 페이지는 전체 분량을 "500일 분량, 2,000개 이상의 학습 콘텐츠"로 소개함.
[출처: https://www.speak.com/ko/content]
2024년판 소개 페이지는 같은 분량을 "17개의 코스로 세분화된 500일 분량"으로 설명함.
[출처: https://www.speak.com/ko/content-2024]
sitemap.xml 조사 결과 실제 코스 URL은 17개, 코스별 day 페이지 합계는 469개로 실측됨.
[출처: https://www.speak.com/sitemap.xml, 2026-09-26 실측]
스픽의 수업은 오늘의 수업, 스피킹 연습, 실전 대화의 3단계로 진행된다고 설명함.
[출처: https://www.speak.com/ko/content]
AI 튜터 기능은 롤플레이 90개 이상, 프리토킹 주제 120개 이상을 제공한다고 밝힘.
[출처: https://www.speak.com/ko/ai-tutor]

## 2. 전체 커리큘럼 구조 — 현재 마케팅 페이지 기준

https://www.speak.com/ko/content 페이지는 커리큘럼을 CEFR 5단계로 소개함.
아래 표는 그 페이지에 나열된 레벨과 코스명을 그대로 옮긴 것임.
[출처: https://www.speak.com/ko/content, 2026-09-26 확인]

| CEFR 레벨 | 스픽 레벨명 | 나열된 코스명 |
|---|---|---|
| A1 | 왕초보 | 스피킹하며 시작 (왕초보 1탄) |
| A2 | 초보 | 초급 1, 초급 2, 초급 3, 스피킹하며 시작 (왕초보 2탄), 영어적 사고 기르기, 스피킹 살아남기 (기초 1탄), 스피킹 살아남기 (기초 2탄), 여행 영어 1, 여행 영어 2, 엄마빠 영어 |
| B1 | 중급 | 중급 1, 중급 2, 중급 3, 스피킹 살아남기 (기초 3탄), 원어민처럼 스피킹, 패턴으로 말하기, 구동사 격파 1탄, 구동사 격파 2탄, 실전 상황별 스피킹, 영어 면접 대비, 대학 캠퍼스 영어1 |
| B2 | 고급 | 고급 1, 고급 2, 깊이 있는 스피킹 (고급 1탄), 깊이 있는 스피킹 (고급 2탄), 비즈니스 (회사생활 영어), 비즈니스 (실무 영어), 직장인을 위한 비즈니스 영어, 영어면접: 이젠 두렵지 않다!, 대학 캠퍼스 영어2 |
| C1 | 마스터 | 마스터 |

위 표의 코스명을 낱개로 세면 32개가 나옴. 이 숫자는 사이트가 직접 밝힌 값이 아니라 문서 작성자가 직접 집계한 값임.
[집계 근거: 위 표, 2026-09-26 집계]
사이트는 이 32개 코스명이 서로 다른 32개 상품 단위인지, 하나의 코스 안에서 다시 나뉜 하위 단위인지 명시하지 않음.
그러므로 32라는 숫자와 3장의 실측 코스 수(17개)가 다른 이유는 미확인으로 남김.

## 3. 실측 코스 구조 — sitemap.xml 기준

https://www.speak.com/sitemap.xml 에 course-list와 course-day-list라는 두 URL 패턴이 있음.
[출처: https://www.speak.com/sitemap.xml, 2026-09-26 실측]
course-list는 코스 1개당 1페이지이며 총 17개가 등록되어 있음.
course-day-list는 코스 안의 하루 학습(레슨) 1개당 1페이지이며 총 469개가 등록되어 있음.
course-list 페이지(예: https://www.speak.com/course-list/01-basics-0)는 직접 접속하면 본문이 없이 "No items found."만 표시됨.
이는 웹플로우(Webflow) CMS의 컬렉션 목록이 원래 페이지의 맥락(현재 항목 필터) 안에서만 채워지는 구조이고, 직접 접속에서는 그 필터가 걸리지 않아 빈 결과가 나오는 것으로 추정함.
[근거: curl 실측, 2026-09-26, 17개 course-list URL 모두 동일하게 58086바이트의 빈 템플릿]
course-day-list 페이지도 마찬가지로 필터 없이 열리며, URL이 달라도 항상 같은 내용(6352자)이 나옴.
[근거: curl 실측, 2026-09-26, 469개 중 4개 표본 URL이 모두 동일한 본문]
그러므로 course-day-list의 본문은 특정 코스와 특정 day 하나만의 내용이 아니라 컬렉션의 고정된 일부 샘플로 판단함.
아래 표는 course-list URL의 slug(코스 코드)와 sitemap에서 실측한 코스별 day 페이지 수임.
코스명 칸은 확인, 추정, 미확인으로 구분해 표시함.

| 순번 | 코스 코드 | day 수(실측) | 추정 코스명 | 근거 상태 |
|---|---|---|---|---|
| 01 | basics-0 | 27 | 스피킹하며 시작 (왕초보 1탄) | 추정 |
| 02 | basics-0-2 | 27 | 스피킹하며 시작 (왕초보 2탄) | 추정 |
| 03 | basics-0-3 | 29 | 영어적 사고 기르기 | 추정 |
| 04 | basics-1 | 31 | 스피킹 살아남기 (기초 1탄) | 추정 |
| 05 | basics-1-2 | 31 | 스피킹 살아남기 (기초 2탄) | 추정 |
| 06 | basics-1-3 | 31 | 스피킹 살아남기 (기초 3탄) | 추정 |
| 07 | basics-2 | 31 | 미확인 | 미확인 |
| 08 | basics-2-2 | 31 | 미확인 | 미확인 |
| 09 | basics-2-3 | 31 | 미확인 | 미확인 |
| 10 | be-1 | 29 | 비즈니스 (회사생활 영어) 계열 | 추정 |
| 11 | be-2 | 28 | 비즈니스 (실무 영어) 계열 | 추정 |
| 12 | bi-1 | 32 | 영어 면접 관련 코스 | 추정 |
| 13 | me-1 | 27 | 엄마빠 영어 | 확인 |
| 14 | pv-1 | 22 | 구동사 격파 1탄 | 확인 |
| 15 | pv-2 | 22 | 구동사 격파 2탄 | 확인 |
| 16 | te-1 | 23 | 여행 영어 1 | 확인 |
| 17 | te-2 | 17 | 여행 영어 2 | 확인 |

day 수의 합계는 469로, course-day-list의 sitemap 등록 개수와 일치함.
[출처: sitemap.xml, 2026-09-26 실측 합산]
확인 표시는 7장의 시나리오 예시 문장 내용과 day 수가 함께 들어맞아 판단한 것이고, 사이트가 코스명을 직접 이름표로 붙여 보여준 것은 아님.
추정 표시는 코스 코드(be, bi, basics 등)와 2장 코스명 목록의 순서와 성격을 견주어 판단한 것임.
me, pv, te라는 코드는 각각 엄마와 아빠, 구동사(phrasal verb), 여행(travel)의 머리글자로 추정하나 사이트가 이 대응을 밝히지 않아 미확인임.

## 4. 두 구조 사이의 불일치

2장의 마케팅 페이지는 코스명을 32개 나열하고 5단계 CEFR 레벨로 나눔.
3장의 sitemap 실측은 코스 URL을 17개, day 페이지를 469개로 보여줌.
2024년판 페이지는 "17개의 코스로 세분화된 500일 분량"이라고 밝혀 3장의 17과 일치함.
[출처: https://www.speak.com/ko/content-2024]
그러므로 3장의 17개 코드는 2024년 시점 커리큘럼 구조로 보이고, 2장의 32개 코스명은 그 뒤에 늘어난 현재 마케팅 페이지의 코스 목록으로 추정함.
두 구조가 어떻게 대응하는지, 코스가 실제로 늘었는지는 사이트에서 확인할 수 없어 미확인으로 남김.
"500일"이라는 문구는 두 시점 모두 동일하게 쓰이는데 3장의 실측 합계는 469일이라 정확히 일치하지 않음.
이 차이가 반올림 표현인지, 집계 시점 차이인지는 미확인임.

## 5. 학습 모드와 기능

### 5-1. 3단계 학습법

스픽은 각 수업을 오늘의 수업, 스피킹 연습, 실전 대화의 3단계로 구성한다고 설명함.
[출처: https://www.speak.com/ko/content]
한 수업(약 20분) 동안 이 3단계를 통해 100문장 이상을 소리 내어 말하게 된다고 설명함.
[출처: https://www.speak.com/ko/content]

### 5-2. 순환 학습과 누적 학습

스픽은 이 3단계 학습을 순환 반복하며 표현을 내재화한다고 설명함.
[출처: https://www.speak.com/ko/content]
순환 학습으로 익힌 표현이 누적되어 특정 분야와 상황에서의 실력으로 쌓인다고 설명함.
[출처: https://www.speak.com/ko/content]

### 5-3. 스마트 리뷰(간격 반복 학습)

스마트 리뷰는 배운 영어 패턴을 자동으로 복습 항목에 저장하고 복습 수업을 제공한다고 설명함.
[출처: https://www.speak.com/ko/content]
간격 반복 학습 알고리즘으로 표현이 영구적으로 기억되도록 돕는다고 설명함.
[출처: https://www.speak.com/ko/content]

### 5-4. AI 발음 코치

스픽은 학습자의 발음을 음소 단위로 분석한다고 설명함.
[출처: https://www.speak.com/ko/content]
학습자 발음과 모범 발음을 실시간으로 대조해 교정 안내를 준다고 설명함.
[출처: https://www.speak.com/ko/content]

### 5-5. AI 프리톡과 비주얼 모드

AI 프리톡은 원어민 없이도 원하는 상황과 주제로 자유롭게 대화하는 기능이라고 설명함.
[출처: https://www.speak.com/ko/content]
대화 중 단어와 문장에 실시간 피드백을 주고 맞춤형 복습 수업을 생성한다고 설명함.
[출처: https://www.speak.com/ko/content]
비주얼 모드는 사용자가 정한 상대와 상황 속에서 더 몰입감 있는 프리톡을 제공한다고 설명함.
[출처: https://www.speak.com/ko/content]

### 5-6. AI 튜터(롤플레이·프리토킹)

AI 튜터는 정해진 표현을 따라 하는 방식을 넘어 원하는 주제로 실제 대화를 할 수 있는 수업이라고 설명함.
[출처: https://www.speak.com/ko/ai-tutor]
AI 튜터 안에는 롤플레이 수업, 프리토킹 수업, 자유 토픽 롤플레이 수업의 세 가지 유형이 있다고 설명함.
[출처: https://www.speak.com/ko/ai-tutor]
실전상황 롤플레이는 90개 이상, 주제별 프리토킹은 120개 이상이라고 밝힘.
[출처: https://www.speak.com/ko/ai-tutor]
구체적인 롤플레이 상황명이나 프리토킹 주제명은 이 페이지에 나열되어 있지 않아 미확인임.
[출처: https://www.speak.com/ko/ai-tutor]

### 5-7. 음성 인식과 분석 기술

스픽은 자체 개발한 음성 인식 AI로 핵심 기능을 구현한다고 설명함.
[출처: https://www.speak.com/ko/technology]
원어민 음성 데이터와 100만 명 이상의 한국인 음성 데이터를 함께 학습시켰다고 설명함.
[출처: https://www.speak.com/ko/technology]
음성 인식 정확도는 93% 이상이라고 밝힘.
[출처: https://www.speak.com/ko/technology]
한국인 영어 학습 데이터를 2만 시간 이상 모아 문화적 표현 차이를 인지하고 안내한다고 설명함.
[출처: https://www.speak.com/ko/technology]

## 6. 레슨 진행 흐름 — 확인 가능한 범위

마케팅 페이지 기준으로 레슨 진행 흐름은 오늘의 수업, 스피킹 연습, 실전 대화의 순서로 소개됨.
[출처: https://www.speak.com/ko/content]
이 3단계 각각이 앱 화면에서 정확히 어떤 문제 유형과 상호작용으로 이루어지는지는 로그인 화면 안쪽 정보라 미확인임.
유닛(unit)이라는 용어를 스픽이 직접 쓰는지는 조사한 페이지들에서 확인하지 못해 미확인임.
사이트가 쓰는 단위는 레벨(A1~C1), 코스, day(하루 학습)로 확인됨.
[출처: https://www.speak.com/ko/content, https://www.speak.com/sitemap.xml]

## 7. 시나리오와 주제 예시 — 실제로 확인된 문장

아래 예시는 https://www.speak.com/course-day-list/001-basics-0-day-0 등 course-day-list 페이지에서 실제로 관측한 본문 문장임.
[출처: https://www.speak.com/course-day-list/001-basics-0-day-0, 2026-09-26 실측]
3장에서 설명했듯 이 페이지는 코스별로 필터링되지 않은 고정 샘플이라, 각 문장이 정확히 어느 day에 속하는지는 참고용으로만 씀.
아래 표의 day 열은 관측된 화면 표시값이며, 실제 그 코스의 정식 day 번호와 다를 수 있음.

| 추정 코스 | day | 영어 문장 | 한국어 문장 |
|---|---|---|---|
| 여행 영어 계열 | Day 0 | Excuse me, but this pasta is overcooked | 저기요, 파스타가 너무 불었어요. |
| 여행 영어 계열 | Day 2 | Can I get a Number 1 as a meal? | 1번 세트 메뉴로 주세요. |
| 여행 영어 계열 | Day 0 | Could you recommend a good restaurant with local vibes? | 로컬 맛집 추천해주실래요? |
| 여행 영어 계열 | Day 9 | How many more stops to the station? | 역까지 몇 정거장 더 남았나요? |
| 여행 영어 계열 | Day 12 | I'll take it if you throw in this keychain. | 서비스로 열쇠고리 하나 주세요. (흥정하기) |
| 여행 영어 계열 | Day 6 | Customs & Immigration at the Airport 1 | 입국 심사 통과하기 1탄 |
| 여행 영어 계열 | Day 12 | Staying at an Airbnb and a guest house | 에어비앤비, 게스트하우스 |
| 여행 영어 계열 | Day 20 | Where is the lost and found? | 분실물 센터가 어디 있나요? |
| 여행 영어 계열 | Day 21 | Staying safe as a tourist | 안전한 시티투어의 필수표현 |
| 구동사 격파 계열 | Day 17 | Jonathan and I don't get along. | 조나단이랑 나는 사이가 안 좋아. |
| 구동사 격파 계열 | Day 18 | I can't get by on this salary. | 이 연봉으로는 먹고살 수 없어. |
| 구동사 격파 계열 | Day 9 | Facebook took over Instagram. | 페이스북이 인스타그램을 인수했어. |
| 구동사 격파 계열 | Day 15 | I'm getting over my fear of speaking. | 영어 회화 울렁증을 극복해 나가고 있어. |
| 구동사 격파 계열 | Day 17 | I need to get rid of the piano before I move. | 이사가기 전에 피아노를 처분해야 해. |
| 구동사 격파 계열 | Day 0 | I need to pick up my girlfriend from the airport. | 공항에서 여자친구 데려 와야 해. |
| 엄마빠 영어 | Day 12 | You have to get ready for school. | 학교 갈 준비 해야 돼. |
| 엄마빠 영어 | Day 18 | Inside voice only. | 조용조용히 말하자. |
| 엄마빠 영어 | Day 25 | Time for a bubble bath. | 목욕할 시간이야. |
| 엄마빠 영어 | Day 16 | Does she have any trouble keeping up in class? | 우리 애가 수업을 잘 따라가고 있나요? |

리뷰 데이(Review Day)라는 항목도 관측됨. 여러 day를 묶어 복습하는 코스 안의 단위로 추정함.
[출처: https://www.speak.com/course-day-list/001-basics-0-day-0, 2026-09-26 실측]
예: "Review Day / 활용도 100% 맛집 및 카페 투어 표현", "Review Day / 시티 투어 필수 표현 총정리"
AI 튜터의 롤플레이와 프리토킹 주제명 목록은 5-6절에서 밝힌 대로 사이트에 나열되어 있지 않아 미확인임.

## 8. 미확인 사항 정리

다음은 이 조사에서 끝내 확인하지 못한 항목임. 추측을 사실처럼 적지 않고 그대로 남김.

1. 32개 마케팅 코스명과 17개 실측 코스 코드의 정확한 대응 관계는 미확인임.
2. basics-2, basics-2-2, basics-2-3 세 코스의 실제 이름은 미확인임.
3. be-1, be-2, bi-1 코스의 정확한 이름과 be, bi가 가리키는 말의 정확한 뜻은 미확인임.
4. me, pv, te 코드가 정말 엄마와 아빠, phrasal verb, travel의 머리글자인지는 미확인임.
5. AI 튜터 롤플레이 90개, 프리토킹 120개의 구체적인 상황명과 주제명 목록은 미확인임.
6. 유닛(unit)이라는 용어를 스픽이 실제로 쓰는지는 미확인임.
7. 로그인 후 실제 앱 화면에서 3단계 학습법이 화면 단위로 어떻게 구현되는지는 미확인임.
8. "500일"과 실측 469일의 차이가 반올림인지 시점 차이인지는 미확인임.
9. https://www.speak.com/en/content 는 404 응답이라 영어판 커리큘럼 페이지 경로 자체가 다른지, 없는지는 미확인임.
[출처: https://www.speak.com/en/content, 2026-09-26 확인, HTTP 404]

## 9. 출처 목록

- https://www.speak.com/ko/content (2026-09-26 확인)
- https://www.speak.com/ko/technology (2026-09-26 확인)
- https://www.speak.com/ko/ai-tutor (2026-09-26 확인)
- https://www.speak.com/ko/content-2024 (2026-09-26 확인, 2024년판 아카이브 페이지)
- https://www.speak.com/en/content (2026-09-26 확인, HTTP 404)
- https://help.speak.com/ko/ (2026-09-26 확인, 카테고리 목록만 확인)
- https://www.speak.com/sitemap.xml (2026-09-26 확인)
- https://www.speak.com/course-list/01-basics-0 (2026-09-26 확인, 대표 예시, 17개 URL 모두 같은 결과)
- https://www.speak.com/course-day-list/001-basics-0-day-0 (2026-09-26 확인, 대표 예시, 표본 4개 URL 모두 같은 결과)
