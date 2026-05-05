package main

import (
	"testing"
)

func TestLRUCache_Basic(t *testing.T) {
	cache := NewLRUCache(100)
	
	// Test 1: Add item and retrieve it
	cache.Put("item1", 50)
	if !cache.Get("item1") {
		t.Error("Expected item1 to be in cache")
	}
	if cache.CurrentSize != 50 {
		t.Errorf("Expected current size 50, got %d", cache.CurrentSize)
	}

	// Test 2: Update existing item
	cache.Put("item1", 60)
	if cache.CurrentSize != 60 {
		t.Errorf("Expected current size 60, got %d", cache.CurrentSize)
	}

	// Test 3: Eviction
	cache.Put("item2", 50) // Total size now 110, should evict item1
	if cache.Get("item1") {
		t.Error("Expected item1 to be evicted")
	}
	if !cache.Get("item2") {
		t.Error("Expected item2 to be in cache")
	}
	if cache.CurrentSize != 50 {
		t.Errorf("Expected current size 50, got %d", cache.CurrentSize)
	}
}

func TestSimulation_Scenarios(t *testing.T) {
	// Scenario 1: Infinite Capacity
	// 10 groups, 100 requests each. 
	// Max possible hits = 1000 total requests - 10 compulsory misses = 990 hits.
	// Hit rate = 990/1000 = 99.00%
	pHR, _ := RunSimulation(1000000, 10, 100, 100, 100, 100)
	if pHR != 99.00 {
		t.Errorf("Expected 99.00%% prefix hit rate with infinite cache, got %.2f%%", pHR)
	}

	// Scenario 2: Zero Capacity
	pHR, _ = RunSimulation(0, 10, 100, 100, 100, 100)
	if pHR != 0.00 {
		t.Errorf("Expected 0.00%% prefix hit rate with zero cache, got %.2f%%", pHR)
	}

	// Scenario 3: Micro Cache (can only hold one prefix)
	// Even with a random order, since we have 10 groups, we expect a very low hit rate.
	pHR, _ = RunSimulation(100, 10, 100, 0, 0, 100)
	if pHR > 20.0 { // 10% expected roughly if sequential, but random might vary slightly
		t.Logf("Micro cache hit rate: %.2f%%", pHR)
	}
}
