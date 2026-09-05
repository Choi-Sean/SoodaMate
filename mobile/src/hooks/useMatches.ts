import { useQuery } from "@tanstack/react-query";

import { getMatches } from "../api/matches";

export function useMatches() {
  return useQuery({ queryKey: ["matches"], queryFn: getMatches });
}
