import random

def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
            yield j + 1

def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
            yield i
        arr[j + 1] = key
        yield i

def selection_sort(arr):
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
            yield j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
        yield i

def merge_sort(arr):
    def merge(start, mid, end):
        left = arr[start:mid]
        right = arr[mid:end]
        i = j = 0
        for k in range(start, end):
            if i < len(left) and (j >= len(right) or left[i] <= right[j]):
                arr[k] = left[i]
                i += 1
            else:
                arr[k] = right[j]
                j += 1
            yield k
    def _merge_sort(start, end):
        if end - start > 1:
            mid = (start + end) // 2
            yield from _merge_sort(start, mid)
            yield from _merge_sort(mid, end)
            yield from merge(start, mid, end)
    yield from _merge_sort(0, len(arr))

def quick_sort(arr):
    def _quick_sort(start, end):
        if start < end:
            pivot = arr[end - 1]
            i = start
            for j in range(start, end - 1):
                if arr[j] < pivot:
                    arr[i], arr[j] = arr[j], arr[i]
                    i += 1
                yield j
            arr[i], arr[end - 1] = arr[end - 1], arr[i]
            yield i
            yield from _quick_sort(start, i)
            yield from _quick_sort(i + 1, end)
    yield from _quick_sort(0, len(arr))

def heap_sort(arr):
    def heapify(n, i):
        largest = i
        l = 2 * i + 1
        r = 2 * i + 2
        if l < n and arr[l] > arr[largest]:
            largest = l
        if r < n and arr[r] > arr[largest]:
            largest = r
        if largest != i:
            arr[i], arr[largest] = arr[largest], arr[i]
            yield largest
            yield from heapify(n, largest)
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        yield from heapify(n, i)
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        yield i
        yield from heapify(i, 0)
