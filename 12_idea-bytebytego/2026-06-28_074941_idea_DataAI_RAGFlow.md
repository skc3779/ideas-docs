실행시간 : 2026-06-28_074941

# [아이디어 상세 실행 문서] RAG-Flow Orchestrator (래그플로우 오케스트레이터)

## 1. 아이디어명
- **RAG-Flow Orchestrator (래그플로우 오케스트레이터)**: Graph RAG 및 Agentic RAG 통합 DataOps 플랫폼

---

## 2. 제안 범위 및 카테고리
- **대범위**: 데이터 및 인공지능 (Data & AI)
- **중분류/소분류**: MLOps / LLM Apps 파이프라인

---

## 3. 해결 문제와 사용자 페르소나

### 해결하고자 하는 문제 (Pain Point)
1. 기업 지식 베이스를 LLM과 연동할 때, 단순 문서 검색(Vector RAG)으로는 복잡한 추론이나 데이터 간의 관계 파악에 한계가 있어 환각(Garbage out)이 발생합니다.
2. 이를 극복하기 위해 지식 그래프를 활용한 'Graph RAG'나, 능동적으로 웹 검색 및 툴을 호출하는 'Agentic RAG'가 도입되고 있으나, 이 파이프라인들을 구축하고 관리하기 위한 MLOps 시스템이 매우 복잡합니다.

### 사용자 페르소나
- **AI/데이터 엔지니어**: 회사 내 수만 건의 매뉴얼과 DB를 기반으로 사내 AI 챗봇을 구축 중입니다. 질문 유형에 따라 가벼운 SLM(Small Language Model) 기반의 단순 RAG로 보낼지, 무거운 LLM 기반의 Graph RAG로 보낼지 트래픽을 지능적으로 라우팅하고 싶습니다.

---

## 4. 핵심 기능 및 차별점

### 핵심 기능
1. **인텐트 기반 동적 라우팅 (Intent Routing)**: 사용자의 질의를 분석하여 "사실 검색"은 일반 Vector RAG로, "원인 분석 및 다중 엔티티 추론"은 Graph RAG로, "외부 API 연동 및 액션"은 Agentic RAG로 자동 스위칭합니다.
2. **Garbage In 억제(데이터 전처리) 필터**: 마거릿 애트우드의 경고처럼 데이터 오염을 막기 위해, RAG 파이프라인에 입력되는 원본 문서의 일관성, 최신성, 신뢰도를 LLM이 교차 검증하여 저품질 문서를 사전에 배제합니다.
3. **지식 그래프 자동 생성 시각화 UI**: 문서 뭉치를 업로드하면 내부적으로 엔티티를 추출해 Graph RAG용 지식 그래프를 자동 생성하고 시각적으로 수정할 수 있는 노드 에디터를 제공합니다.

### 차별점
- 단일 RAG 솔루션이 아니라, **현존하는 세 가지 RAG 방식(Vector, Graph, Agentic)을 모듈화하여 가장 비용 효율적인 파이프라인을 조립**할 수 있게 해주는 업계 표준 허브입니다.

---

## 5. 실현 가능성 점수 및 근거
- **실현 가능성 점수**: **4.8 / 5.0** (매우 높음)
- **근거**: LangChain, LlamaIndex 생태계에서 관련 컴포넌트가 이미 쏟아져 나오고 있으므로, 이를 비개발자도 쓸 수 있는 강력한 GUI/API 플랫폼으로 패키징하는 것은 B2B 시장에서 즉시 매출을 일으킬 수 있습니다.

---

## 6. 참고 RSS FEED
- **제목**: EP220: RAG vs Graph RAG vs Agentic RAG
- **링크**: [ByteByteGo](https://blog.bytebytego.com/p/ep220-rag-vs-graph-rag-vs-agentic)
- **제목**: Margaret Atwood says the problem with AI is 'garbage in, garbage out'
- **링크**: [The Verge](https://www.theverge.com/ai-artificial-intelligence/958715/margaret-atwood-ai-problem-garbage-in-garbage-out)
