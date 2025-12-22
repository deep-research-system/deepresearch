// Server-Sent Events (SSE) 유틸리티 함수

// SSE 이벤트 타입과 데이터 구조 정의
// event: 시스템메시지, data : 실제메시지
export type SseEvent = {
    event: string;
    data: any;
  };
  
  // SSE 메시지("event: ...\ndata: ...")를 data와 event로 따로 파싱
  export function parseSseBlock(block: string): SseEvent | null {
    let event = "message";
    let dataStr = "";
  
    const lines = block.split("\n");
    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        // data:가 여러 줄일 수 있어 누적
        dataStr += line.slice("data:".length).trim();
      }
    }
  
    if (!dataStr) return { event, data: null };
  
    // data: 부분만 JSON이라고 가정하고 파싱
    try {
      return { event, data: JSON.parse(dataStr) };
    } catch {
      // data가 JSON이 아닐 수도 있는 설계를 할 거면 여기서 처리
      return { event, data: dataStr };
    }
  }
  
  // Response 스트림을 읽으면서 SSE 이벤트 단위로 파싱하여 콜백 호출
  // 콜백 : 나중에 어떤 일이 발생했을 때 실행하도록 넘겨주는 함수
  export async function readSseStream(
    res: Response,
    // onevent : 이벤트 하나씩 처리할 콜백
    onEvent: (evt: SseEvent) => void
  ): Promise<void> {
    if (!res.body) throw new Error("No response body (stream not available).");
    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    
    // 스트림이 임의의 크기로 잘려 들어오기 때문에 누적버퍼 필요
    let buffer = "";

    // 서버가 닫힐때까지 읽기(실시간)
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
  
      buffer += decoder.decode(value, { stream: true });
  
      // SSE는 이벤트 하나가 \n\n 로 끝남
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      // 이벤트 파싱 & 콜백 호출
      for (const part of parts) {
        const evt = parseSseBlock(part);
        if (evt) onEvent(evt);
      }
    }
  }
  