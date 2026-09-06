import { useQuery } from "@tanstack/react-query";

import { getSwipeLimit } from "../api/interactions";

export function useSwipeLimit() {
  return useQuery({ queryKey: ["swipeLimit"], queryFn: getSwipeLimit });
}
