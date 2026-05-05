package main

import (
	"container/list"
	"fmt"
	"math/rand"
	"os"
	"strconv"
	"time"
)

// CacheItem represents an entry in the LRU cache.
type CacheItem struct {
	Key  string
	Size int
}

// LRUCache implements a size-based LRU cache.
type LRUCache struct {
	Capacity    int
	CurrentSize int
	items       map[string]*list.Element
	evictList   *list.List
}

func NewLRUCache(capacity int) *LRUCache {
	return &LRUCache{
		Capacity:  capacity,
		items:     make(map[string]*list.Element),
		evictList: list.New(),
	}
}

// Get checks if a key exists in the cache and moves it to the front.
func (c *LRUCache) Get(key string) bool {
	if ent, ok := c.items[key]; ok {
		c.evictList.MoveToFront(ent)
		return true
	}
	return false
}

// Put adds a key with a specific size to the cache, evicting items if necessary.
func (c *LRUCache) Put(key string, size int) {
	if size > c.Capacity {
		// If a single item is larger than the entire cache, we can't store it.
		return
	}

	// If key already exists, update size and move to front
	if ent, ok := c.items[key]; ok {
		c.evictList.MoveToFront(ent)
		item := ent.Value.(*CacheItem)
		c.CurrentSize -= item.Size
		item.Size = size
		c.CurrentSize += size
	} else {
		// Add new item
		ent := c.evictList.PushFront(&CacheItem{Key: key, Size: size})
		c.items[key] = ent
		c.CurrentSize += size
	}

	// Evict items if capacity exceeded
	for c.CurrentSize > c.Capacity {
		c.removeOldest()
	}
}

func (c *LRUCache) removeOldest() {
	ent := c.evictList.Back()
	if ent != nil {
		item := ent.Value.(*CacheItem)
		delete(c.items, item.Key)
		c.evictList.Remove(ent)
		c.CurrentSize -= item.Size
	}
}

type Request struct {
	GroupID int
	ReqID   int
}

func RunSimulation(cacheSize, numGroups, prefixSize, questionSize, outputSize, reqsPerGroup int) (float64, float64) {
	totalRequests := numGroups * reqsPerGroup
	workload := make([]Request, 0, totalRequests)
	for g := 0; g < numGroups; g++ {
		for r := 0; r < reqsPerGroup; r++ {
			workload = append(workload, Request{GroupID: g, ReqID: g*reqsPerGroup + r})
		}
	}

	rand.Seed(time.Now().UnixNano())
	rand.Shuffle(len(workload), func(i, j int) {
		workload[i], workload[j] = workload[j], workload[i]
	})

	cache := NewLRUCache(cacheSize)
	prefixHits := 0
	totalPrefixTokensHit := 0
	totalTokensRequested := 0

	for _, req := range workload {
		prefixKey := fmt.Sprintf("p_%d", req.GroupID)
		questionKey := fmt.Sprintf("q_%d", req.ReqID)
		outputKey := fmt.Sprintf("o_%d", req.ReqID)

		// Prefix Access
		if cache.Get(prefixKey) {
			prefixHits++
			totalPrefixTokensHit += prefixSize
		} else {
			cache.Put(prefixKey, prefixSize)
		}

		// Question/Output Access (always misses)
		cache.Put(questionKey, questionSize)
		cache.Put(outputKey, outputSize)

		totalTokensRequested += (prefixSize + questionSize + outputSize)
	}

	prefixHitRate := float64(prefixHits) / float64(totalRequests) * 100
	tokenHitRate := float64(totalPrefixTokensHit) / float64(totalTokensRequested) * 100
	return prefixHitRate, tokenHitRate
}

func main() {
	if len(os.Args) < 7 {
		fmt.Println("Usage: go run lru_sim.go <cache_size> <num_groups> <prefix_size> <question_size> <output_size> <reqs_per_group>")
		return
	}

	cacheSize, _ := strconv.Atoi(os.Args[1])
	numGroups, _ := strconv.Atoi(os.Args[2])
	prefixSize, _ := strconv.Atoi(os.Args[3])
	questionSize, _ := strconv.Atoi(os.Args[4])
	outputSize, _ := strconv.Atoi(os.Args[5])
	reqsPerGroup, _ := strconv.Atoi(os.Args[6])

	pHR, tHR := RunSimulation(cacheSize, numGroups, prefixSize, questionSize, outputSize, reqsPerGroup)

	fmt.Printf("--- LRU Cache Simulation Results ---\n")
	fmt.Printf("Cache Size:          %d\n", cacheSize)
	fmt.Printf("Total Requests:      %d\n", numGroups*reqsPerGroup)
	fmt.Printf("Prefix Hit Rate:     %.2f%%\n", pHR)
	fmt.Printf("Token Hit Rate:      %.2f%%\n", tHR)
}
