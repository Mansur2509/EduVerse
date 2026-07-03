import type { RecommendationCategory, RecommendationCounts, RecommendationItem } from "@/entities/recommendation";
import type { MajorCluster } from "@/entities/university";

export type RoundBucket =
  | "restrictive_early_action"
  | "early_action"
  | "early_decision_1"
  | "early_decision_2"
  | "regular_decision"
  | "rolling"
  | "international"
  | "unknown_verify_round";

export type RoundConfidence = "verified" | "estimated" | "unverified";

export type StrategySchool = RecommendationItem & {
  round_bucket: RoundBucket;
  round_confidence: RoundConfidence;
};

export type ApplicationStrategyResponse = {
  schools: StrategySchool[];
  by_category: Record<RecommendationCategory, StrategySchool[]>;
  by_round: Record<RoundBucket, StrategySchool[]>;
  by_country: Record<string, StrategySchool[]>;
  by_major_cluster: Record<MajorCluster | "program_data_not_verified", StrategySchool[]>;
  round_bucket_order: RoundBucket[];
  category_order: RecommendationCategory[];
  country_order: string[];
  major_cluster_order: Array<MajorCluster | "program_data_not_verified">;
  counts: RecommendationCounts;
  target_range: { minimum: number; maximum: number };
  data_scarcity: boolean;
  excluded_low_data_count: number;
  missing_preferences: string[];
  disclaimer: string;
};
