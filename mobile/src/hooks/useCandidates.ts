import { useQuery } from "@tanstack/react-query";

import { getCandidates } from "../api/discovery";

export function useCandidates(enabled: boolean = true) {
  return useQuery({ queryKey: ["candidates"], queryFn: () => getCandidates(), enabled });
}
