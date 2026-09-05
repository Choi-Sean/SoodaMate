import { useQuery } from "@tanstack/react-query";

import { getCandidates } from "../api/discovery";

export function useCandidates() {
  return useQuery({ queryKey: ["candidates"], queryFn: () => getCandidates() });
}
