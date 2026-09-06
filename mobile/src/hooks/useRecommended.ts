import { useQuery } from "@tanstack/react-query";

import { getRecommended } from "../api/discovery";

export function useRecommended() {
  return useQuery({ queryKey: ["recommended"], queryFn: () => getRecommended() });
}
