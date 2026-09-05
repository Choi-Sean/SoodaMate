import { useMutation, useQueryClient } from "@tanstack/react-query";

import { swipe, type SwipeAction, type SwipeResult } from "../api/interactions";
import type { Candidate } from "../types";

export function useSwipeAction() {
  const queryClient = useQueryClient();

  return useMutation<SwipeResult, unknown, { action: SwipeAction; candidate: Candidate }>({
    mutationFn: ({ action, candidate }) => swipe(action, candidate.user_id),
    onSuccess: (_result, { candidate }) => {
      // Optimistically drop the swiped candidate so the stack advances
      // immediately instead of waiting on a refetch.
      queryClient.setQueryData<Candidate[]>(["candidates"], (prev) =>
        (prev ?? []).filter((c) => c.user_id !== candidate.user_id)
      );
      if (queryClient.getQueryData<Candidate[]>(["candidates"])?.length === 0) {
        queryClient.invalidateQueries({ queryKey: ["candidates"] });
      }
    },
  });
}
