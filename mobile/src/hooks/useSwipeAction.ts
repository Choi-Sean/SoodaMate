import { useMutation, useQueryClient } from "@tanstack/react-query";

import { swipe, type SwipeAction, type SwipeResult } from "../api/interactions";
import type { Candidate } from "../types";

function dropCandidate(queryClient: ReturnType<typeof useQueryClient>, userId: string) {
  queryClient.setQueryData<Candidate[]>(["candidates"], (prev) =>
    (prev ?? []).filter((c) => c.user_id !== userId)
  );
  if (queryClient.getQueryData<Candidate[]>(["candidates"])?.length === 0) {
    queryClient.invalidateQueries({ queryKey: ["candidates"] });
  }
  queryClient.setQueryData<Candidate[]>(["likedMe"], (prev) =>
    (prev ?? []).filter((c) => c.user_id !== userId)
  );
}

export function useSwipeAction() {
  const queryClient = useQueryClient();

  return useMutation<SwipeResult, unknown, { action: SwipeAction; candidate: Candidate }>({
    mutationFn: ({ action, candidate }) => swipe(action, candidate.user_id),
    onSuccess: (_result, { candidate }) => {
      // Optimistically drop the swiped candidate so the stack advances
      // immediately instead of waiting on a refetch.
      dropCandidate(queryClient, candidate.user_id);
      queryClient.invalidateQueries({ queryKey: ["swipeLimit"] });
    },
    onError: (err: any, { candidate }) => {
      // A 404 means that account was deleted after the deck was fetched —
      // drop the card so the user isn't stuck swiping a ghost. Any other
      // error (429 limit, 402 no-superlikes, network) leaves the card in
      // place so the action can be retried.
      if (err?.response?.status === 404) {
        dropCandidate(queryClient, candidate.user_id);
      }
    },
  });
}
