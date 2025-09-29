# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import json
import re


def get_json_size(js: dict) -> int:
    """Calculate the byte size of a dictionary after converting to JSON string and UTF-8 encoding"""
    return len(json.dumps(js, ensure_ascii=False).encode('utf-8'))


def segments2json_chunks(segments: list[str], chunk_size_max: int) -> tuple[dict[str, str],
list[dict[str, str]], list[tuple[int, int]]]:
    """
    Convert a list of text segments into multiple JSON chunks.
    (Function annotation unchanged)
    """

    # === Part 1: Preprocessing (this logic can remain unchanged) ===
    new_segments = []
    merged_indices_list = []

    for segment in segments:
        # Check if a single segment (as a value in a JSON object) already exceeds the limit
        # Use a longer key for estimation to avoid errors from key length variations
        long_key_estimate = str(len(segments) + len(new_segments))
        if get_json_size({long_key_estimate: segment}) > chunk_size_max:
            sub_segments = []
            lines = segment.splitlines(keepends=True)
            current_sub_segment = ""
            for line in lines:
                next_sub_segment = current_sub_segment + line

                if get_json_size({long_key_estimate: next_sub_segment}) > chunk_size_max:
                    if current_sub_segment:
                        sub_segments.append(current_sub_segment)

                    # Even if a single line exceeds the limit, it must be added as an independent sub-segment
                    sub_segments.append(line)
                    current_sub_segment = ""
                else:
                    current_sub_segment = next_sub_segment

            if current_sub_segment:
                sub_segments.append(current_sub_segment)

            if not sub_segments and segment == "":
                sub_segments.append("")

            start_index = len(new_segments)
            new_segments.extend(sub_segments)
            end_index = len(new_segments)
            if end_index - start_index > 1:
                merged_indices_list.append((start_index, end_index))
        else:
            new_segments.append(segment)

    # === Part 2: Combine into JSON chunks (corrected part) ===
    json_chunks_list = []
    if not new_segments:
        return {}, [], []

    chunk = {}
    for key, val in enumerate(new_segments):
        prospective_chunk = chunk.copy()
        prospective_chunk[str(key)] = val

        # Fix bug: Even if chunk is empty, if prospective_chunk (i.e., single element) exceeds limit,
        # should first submit the old chunk.
        if get_json_size(prospective_chunk) > chunk_size_max and chunk:
            json_chunks_list.append(chunk)
            chunk = {str(key): val}
        else:
            chunk = prospective_chunk

    if chunk:
        json_chunks_list.append(chunk)

    # ==================== Core Correction ====================
    # Build the final, complete js dictionary based on the complete new_segments list
    # This ensures the first return value is complete
    js = {str(i): segment for i, segment in enumerate(new_segments)}
    # =========================================================

    return js, json_chunks_list, merged_indices_list


def fix_json_string(json_string):
    def repl(m:re.Match):
        return f"""{'"' if m.group(1) else ""},\n"{m.group(2)}":{'"' if m.group(3) else ""}"""
    fixed_json = re.sub(
        r"""([“”"])?\s*[，,]\s*["“”]\s*(\d+)\s*["“”]\s*[：:]\s*(["“”])?""",
        repl,
        json_string,
        re.MULTILINE
    )
    return fixed_json


if __name__ == '__main__':
    print(get_json_size({"0": ""}))
