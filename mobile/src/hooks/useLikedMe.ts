import { useQuery } from "@tanstack/react-query";

import { getLikedMe } from "../api/discovery";

export function useLikedMe() {
  return useQuery({ queryKey: ["likedMe"], queryFn: () => getLikedMe() });
}
