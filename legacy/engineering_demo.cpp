// Synthetic legacy application. This executable alone knows the binary layout.
#include <iostream>
#include <fstream>
#include <vector>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <iomanip>
struct Point { double x, y; };
static std::vector<Point> read_run(const char* path) {
    std::ifstream f(path, std::ios::binary);
    char magic[8]; uint32_t count=0; f.read(magic,8); f.read(reinterpret_cast<char*>(&count),4);
    if (!f || std::memcmp(magic,"EWBDEMO1",8)!=0 || count<2 || count>10000) throw std::runtime_error("Invalid or unsupported demo binary");
    std::vector<Point> points(count);
    for(auto &p:points) {
        f.read(reinterpret_cast<char*>(&p.x),8); f.read(reinterpret_cast<char*>(&p.y),8);
        if(!f || !std::isfinite(p.x) || !std::isfinite(p.y)) throw std::runtime_error("Corrupt data");
    }
    if(f.peek()!=EOF) throw std::runtime_error("Unexpected trailing data");
    for(size_t i=1;i<points.size();i++) if(points[i].x<=points[i-1].x) throw std::runtime_error("Samples not ordered");
    return points;
}
int main(int argc,char**argv) {
    try {
        if(argc==3 && std::string(argv[1])=="seed") {
            for(int run=0;run<2;run++) {
                std::string path=std::string(argv[2])+"/run-"+(run?"b":"a")+".ewb";
                std::ofstream f(path,std::ios::binary); uint32_t n=101;
                f.write("EWBDEMO1",8); f.write(reinterpret_cast<char*>(&n),4);
                for(uint32_t i=0;i<n;i++) { double x=i; double y=std::sin(x/14.0)*0.8+0.003*x;
                    if(run) y=y*1.025+0.035*std::exp(-std::pow((x-67)/9,2));
                    f.write(reinterpret_cast<char*>(&x),8); f.write(reinterpret_cast<char*>(&y),8);
                }
                if(!f) throw std::runtime_error("Cannot write demo files");
            }
            std::cout<<"Synthetic binary runs created\n"; return 0;
        }
        if(argc==3 && std::string(argv[1])=="export") {
            auto points=read_run(argv[2]);
            std::cout<<std::setprecision(15)<<"{\"schema\":\"ewb.series/1\",\"reader\":\"engineering-demo/1.0.0\",\"x_unit\":\"sample\",\"y_unit\":\"a.u.\",\"points\":[";
            for(size_t i=0;i<points.size();i++) { if(i)std::cout<<","; std::cout<<"["<<points[i].x<<","<<points[i].y<<"]"; }
            std::cout<<"]}";return 0;
        }
        if(argc==2 && std::string(argv[1])=="version") {std::cout<<"engineering-demo/1.0.0";return 0;}
        std::cerr<<"Usage: engineering-demo seed DIRECTORY | export FILE | version\n";return 2;
    } catch(const std::exception&e) {std::cerr<<e.what()<<"\n";return 1;}
}
