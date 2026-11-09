// iNNOVULIS™ iStick **HOST-SIDE** deterministic 18-slot legal workflow guard.
// This is not a CH340E firmware program, secure-element driver, or legal ruling.
// Builds with C++17; it consumes an already-reviewed TSV manifest only.
#include <array>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct GateSpec { int id; const char* label; bool supplied; };
constexpr std::array<GateSpec, 18> GATES = {{
    {1,"Intake",true}, {2,"Conflict check",true},
    {3,"UNDEFINED",false}, {4,"UNDEFINED",false},
    {5,"Favorable termination",true}, {6,"UNDEFINED",false},
    {7,"Lack of probable cause",true}, {8,"Malice / improper purpose",true},
    {9,"UNDEFINED",false}, {10,"UNDEFINED",false},
    {11,"UNDEFINED",false}, {12,"UNDEFINED",false},
    {13,"UNDEFINED",false}, {14,"Due process notice",true},
    {15,"UNDEFINED",false}, {16,"UNDEFINED",false},
    {17,"UNDEFINED",false}, {18,"Due process reply logged",true}
}};

bool valid_sha256(const std::string& h) {
    if (h.size()!=64) return false;
    for (char c:h) if (!((c>='0'&&c<='9')||(c>='a'&&c<='f'))) return false;
    return true;
}

std::vector<std::string> split_tabs(const std::string& s) {
    std::vector<std::string> cols; std::stringstream ss(s); std::string part;
    while (std::getline(ss,part,'\t')) cols.push_back(part);
    return cols;
}

int main(int argc,char**argv) {
    if (argc!=2) { std::cerr<<"usage: innovulis_istick_host <gate_manifest.tsv>\n";return 2; }
    std::ifstream f(argv[1]);
    if (!f) {std::cerr<<"manifest unavailable\n";return 2;}
    int seen=0, attached=0, contested=0, undefined=0, missing=0;
    std::string line;
    while (std::getline(f,line)) {
        if (seen>=18) {std::cerr<<"too many gates\n";return 3;}
        auto c=split_tabs(line);
        if(c.size()!=4) {std::cerr<<"invalid field count\n";return 3;}
        int id=0;
        try { id=std::stoi(c[0]); }catch(...) {std::cerr<<"invalid ID\n";return 3;}
        if (id!=GATES.at(seen).id) {std::cerr<<"gate order mismatch\n";return 3;}
        if(c[2]!="supplied" && c[2]!="undefined") return 3;
        // No user-supplied definitions for slots 3/4/6/etc were provided.
        // A future approved schema update is required; manifest may not override it.
        if(c[2] != (GATES.at(seen).supplied?"supplied":"undefined")) return 3;
        if(!GATES.at(seen).supplied) ++undefined;
        if(c[1]=="EVIDENCE_ATTACHED" || c[1]=="CONTESTED") {
            if(!valid_sha256(c[3])) {std::cerr<<"invalid evidence hash\n";return 3;}
            if(c[1]=="EVIDENCE_ATTACHED")++attached;else ++contested;
        } else if(c[1]=="NOT_REVIEWED" || c[1]=="MISSING") {
            if(c[3]!="-") return 3;
            ++missing;
        } else {std::cerr<<"unknown gate state\n";return 3;}
        ++seen;
    }
    if(seen!=18) {std::cerr<<"missing gate entries\n";return 3;}
    std::cout<<"{\"device_execution\":\"HOST_ONLY_NOT_FIRMWARE\","
             <<"\"gate_count\":18,\"evidence_attached\":"<<attached
             <<",\"contested\":"<<contested
             <<",\"undefined\":"<<undefined
             <<",\"missing\":"<<missing
             <<",\"legal_merits\":\"NOT_DETERMINED\","
             <<"\"filing_authority\":\"NONE\","
             <<"\"workflow\":\"EVIDENCE_REVIEW_REQUIRED\"}"<<std::endl;
    return 0;
}
